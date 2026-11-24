import threading
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from pipeline import config, db
from pipeline.run import run_pipeline

STATIC = Path(__file__).resolve().parent / "static"
app = FastAPI(title="Report pipeline dashboard", version="1.0.0")
_lock = threading.Lock()
_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = db.get_engine()
    return _engine


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/runs")
def runs():
    rows = db.recent_runs(engine())
    for r in rows:
        r.pop("report_html", None)
        for k in ("started_at", "finished_at"):
            r[k] = r[k].isoformat() if r[k] else None
    return {"runs": rows, "email_enabled": bool(config.SMTP_HOST and config.REPORT_TO)}


@app.get("/api/report/latest", response_class=HTMLResponse)
def latest():
    html = db.latest_report(engine())
    if not html:
        raise HTTPException(404, "No report yet. Run the pipeline first.")
    return html


@app.post("/api/run")
def run_now(x_run_token: str | None = Header(default=None)):
    if config.RUN_TOKEN and x_run_token != config.RUN_TOKEN:
        raise HTTPException(401, "Wrong run token")
    if not _lock.acquire(blocking=False):
        raise HTTPException(409, "A run is already in progress")
    try:
        outcome = run_pipeline(engine())
    finally:
        _lock.release()
    outcome.pop("summary", None)
    return outcome
