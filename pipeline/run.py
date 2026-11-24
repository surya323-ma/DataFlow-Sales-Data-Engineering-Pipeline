"""Pipeline entry point:  python -m pipeline.run"""
import sys
import time
from datetime import datetime, timezone

from . import db, notify
from .clean import clean_orders
from .fetch import fetch_products, read_orders
from .logging_setup import get_logger
from .report import build_summary, render_html, render_text

log = get_logger("pipeline.run")


def run_pipeline(engine=None, sleep=time.sleep) -> dict:
    engine = engine or db.get_engine()
    run_id = db.start_run(engine)
    started = time.perf_counter()
    log.info("Run %d started", run_id)
    try:
        products, source = fetch_products(sleep=sleep)
        raw = read_orders()
        orders, stats = clean_orders(raw, products)
        rows = db.load_orders(engine, orders, products)

        summary = build_summary(orders)
        info = {"source": source, "stats": stats, "finished_at": datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")}
        html, text = render_html(summary, info), render_text(summary)

        emailed = False
        try:
            emailed = notify.send_report(f"Daily sales summary: ${summary['revenue']:,.0f}", html, text)
        except Exception as exc:  # a mail problem must not discard a good run
            log.error("Email failed: %s", exc)

        duration = round(time.perf_counter() - started, 2)
        db.finish_run(engine, run_id, status="success", source=source, rows_loaded=rows, duration_s=duration, emailed=int(emailed), report_html=html)
        log.info("Run %d finished in %.2fs (%d rows, source=%s)", run_id, duration, rows, source)
        return {"run_id": run_id, "status": "success", "rows": rows, "duration_s": duration, "summary": summary}
    except Exception as exc:
        log.exception("Run %d failed", run_id)
        db.finish_run(engine, run_id, status="failed", error=str(exc)[:500], duration_s=round(time.perf_counter() - started, 2))
        return {"run_id": run_id, "status": "failed", "error": str(exc)}


if __name__ == "__main__":
    outcome = run_pipeline()
    sys.exit(0 if outcome["status"] == "success" else 1)
