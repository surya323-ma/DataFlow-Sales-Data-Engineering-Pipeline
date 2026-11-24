import pandas as pd

from pipeline.clean import clean_orders
from pipeline.fetch import fetch_products, read_orders
from pipeline.report import build_summary, flag_anomalies, render_html, render_text


def test_flag_anomalies_finds_spike():
    daily = pd.Series([100, 105, 98, 102, 99, 101, 950], index=[f"d{i}" for i in range(7)])
    assert flag_anomalies(daily) == ["d6"]
    assert flag_anomalies(pd.Series([1, 2, 3])) == []  # too little data to judge


def test_summary_on_sample_data(api_down):
    products, _ = fetch_products(sleep=lambda s: None)
    orders, _ = clean_orders(read_orders(), products)
    summary = build_summary(orders)
    assert summary["orders"] > 200 and summary["revenue"] > 0
    assert len(summary["top_products"]) == 5
    assert "2026-10-17" in summary["anomalies"]  # the deliberate spike in the sample data


def test_empty_summary_and_rendering():
    summary = build_summary(pd.DataFrame())
    assert summary["orders"] == 0
    html = render_html(summary, {"source": "api", "stats": {}})
    assert "Daily sales summary" in html and "No data." in html
    assert "Revenue $0" in render_text(summary)


def test_html_escapes_product_names():
    summary = {"orders": 1, "revenue": 10.0, "avg_order": 10.0, "top_products": [("<script>x</script>", 10.0)],
               "by_category": [], "by_region": [], "daily": [], "anomalies": []}
    assert "<script>" not in render_html(summary, {})
