import json

import pandas as pd

from pipeline import config
from pipeline.clean import clean_orders


def products():
    data = json.loads(config.PRODUCTS_FALLBACK.read_text())
    return pd.DataFrame(data).rename(columns={"id": "product_id", "title": "product", "price": "unit_price"})


def raw(rows):
    return pd.DataFrame(rows, columns=["order_id", "order_date", "customer", "product_id", "quantity", "region"])


def test_removes_duplicates_and_invalid_rows():
    df = raw([
        ["1", "2026-10-01", " asha verma ", "1", "2", "north"],
        ["1", "2026-10-01", " asha verma ", "1", "2", "north"],   # duplicate id
        ["2", "not-a-date", "ravi", "2", "1", "south"],           # bad date
        ["3", "2026-10-02", "neha", "3", "0", "east"],            # zero quantity
        ["4", "2026-10-02", "kabir", "999", "1", "west"],         # unknown product
        ["5", "2026-10-03", None, "2", "3", None],                # blanks are filled, not dropped
    ])
    clean, stats = clean_orders(df, products())
    assert list(clean["order_id"]) == ["1", "5"]
    assert stats["duplicates_removed"] == 1
    assert stats["invalid_removed"] == 2          # bad date + zero quantity
    assert stats["unmatched_products_removed"] == 1


def test_normalises_text_and_computes_revenue():
    clean, _ = clean_orders(raw([["1", "2026-10-01", " asha verma ", "1", "2", " Central "]]), products())
    row = clean.iloc[0]
    assert row["customer"] == "Asha Verma" and row["region"] == "Central"
    assert row["revenue"] == round(2 * 109.95, 2)


def test_unknown_blanks_become_unknown():
    clean, _ = clean_orders(raw([["9", "2026-10-03", None, "2", "3", None]]), products())
    assert clean.iloc[0]["customer"] == "Unknown" and clean.iloc[0]["region"] == "Unknown"
