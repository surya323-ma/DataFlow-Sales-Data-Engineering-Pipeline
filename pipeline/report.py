"""Build the summary report (metrics, anomaly flags, HTML + plain text)."""
from datetime import datetime, timezone
from html import escape

import pandas as pd


def flag_anomalies(daily: pd.Series, k: float = 1.5) -> list[str]:
    """Days whose revenue falls outside the IQR fences (Tukey's rule)."""
    if len(daily) < 4:
        return []
    q1, q3 = daily.quantile(0.25), daily.quantile(0.75)
    iqr = q3 - q1
    low, high = q1 - k * iqr, q3 + k * iqr
    return [str(day) for day, value in daily.items() if value < low or value > high]


def build_summary(orders: pd.DataFrame) -> dict:
    if orders.empty:
        return {"orders": 0, "revenue": 0.0, "avg_order": 0.0, "top_products": [], "by_category": [], "by_region": [], "daily": [], "anomalies": []}
    daily = orders.groupby("order_date")["revenue"].sum().round(2)
    top = orders.groupby("product")["revenue"].sum().nlargest(5).round(2)
    cat = orders.groupby("category")["revenue"].sum().sort_values(ascending=False).round(2)
    region = orders.groupby("region")["revenue"].sum().sort_values(ascending=False).round(2)
    return {
        "orders": int(orders["order_id"].nunique()),
        "revenue": round(float(orders["revenue"].sum()), 2),
        "avg_order": round(float(orders["revenue"].mean()), 2),
        "top_products": [(p, float(v)) for p, v in top.items()],
        "by_category": [(c, float(v)) for c, v in cat.items()],
        "by_region": [(r, float(v)) for r, v in region.items()],
        "daily": [(str(d), float(v)) for d, v in daily.items()],
        "anomalies": flag_anomalies(daily),
    }


def _bars(rows: list[tuple[str, float]], color: str) -> str:
    if not rows:
        return "<p>No data.</p>"
    peak = max(v for _, v in rows) or 1
    out = []
    for label, value in rows:
        width = max(2, round(value / peak * 100))
        out.append(
            f'<tr><td style="padding:4px 10px 4px 0;font-size:13px;white-space:nowrap">{escape(str(label))[:42]}</td>'
            f'<td style="width:100%"><div style="background:{color};height:12px;width:{width}%;border-radius:3px"></div></td>'
            f'<td style="padding-left:10px;font-size:13px;text-align:right;white-space:nowrap">${value:,.0f}</td></tr>'
        )
    return f'<table style="width:100%;border-collapse:collapse">{"".join(out)}</table>'


def render_html(summary: dict, run_info: dict) -> str:
    """Inline-styled HTML so it renders the same in an email client and in the dashboard."""
    anomalies = ", ".join(summary["anomalies"]) or "none"
    stamp = run_info.get("finished_at") or datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    stats = run_info.get("stats", {})
    return f"""<div style="font-family:Arial,Helvetica,sans-serif;color:#1d1f3a;max-width:640px;margin:0 auto;padding:8px">
<h2 style="margin:0 0 4px">Daily sales summary</h2>
<p style="margin:0 0 18px;color:#5b5f86;font-size:13px">Generated {escape(str(stamp))} &middot; product data source: {escape(str(run_info.get("source", "api")))}</p>
<table style="width:100%;border-collapse:separate;border-spacing:8px 0;margin:0 -8px 18px"><tr>
<td style="background:#eef0fb;border-radius:8px;padding:12px"><div style="font-size:22px;font-weight:bold">${summary["revenue"]:,.0f}</div><div style="font-size:12px;color:#5b5f86">Revenue</div></td>
<td style="background:#eef0fb;border-radius:8px;padding:12px"><div style="font-size:22px;font-weight:bold">{summary["orders"]}</div><div style="font-size:12px;color:#5b5f86">Orders</div></td>
<td style="background:#eef0fb;border-radius:8px;padding:12px"><div style="font-size:22px;font-weight:bold">${summary["avg_order"]:,.2f}</div><div style="font-size:12px;color:#5b5f86">Average order</div></td></tr></table>
<h3 style="margin:18px 0 6px;font-size:15px">Top products</h3>{_bars(summary["top_products"], "#2b2d6e")}
<h3 style="margin:18px 0 6px;font-size:15px">Revenue by category</h3>{_bars(summary["by_category"], "#ff6b57")}
<h3 style="margin:18px 0 6px;font-size:15px">Revenue by region</h3>{_bars(summary["by_region"], "#5a62c9")}
<h3 style="margin:18px 0 6px;font-size:15px">Unusual days</h3><p style="font-size:14px;margin:0">{escape(anomalies)}</p>
<p style="margin:22px 0 0;font-size:12px;color:#5b5f86">Data quality: {stats.get("clean_rows", "?")} clean rows from {stats.get("raw_rows", "?")} raw rows ({stats.get("duplicates_removed", 0)} duplicates and {stats.get("invalid_removed", 0)} invalid rows removed).</p>
</div>"""


def render_text(summary: dict) -> str:
    lines = [f"Revenue ${summary['revenue']:,.0f} from {summary['orders']} orders (average ${summary['avg_order']:,.2f})", "Top products:"]
    lines += [f"  - {name}: ${value:,.0f}" for name, value in summary["top_products"]]
    lines.append("Unusual days: " + (", ".join(summary["anomalies"]) or "none"))
    return "\n".join(lines)
