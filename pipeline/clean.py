"""Transform step: tidy raw orders with pandas and join product details."""
import pandas as pd

from .logging_setup import get_logger

log = get_logger("pipeline.clean")


def clean_orders(raw: pd.DataFrame, products: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    stats = {"raw_rows": len(raw)}
    df = raw.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    df = df.drop_duplicates(subset="order_id", keep="first")
    stats["duplicates_removed"] = stats["raw_rows"] - len(df)

    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce")
    df["customer"] = df["customer"].fillna("Unknown").str.strip().str.title()
    df["region"] = df["region"].fillna("Unknown").str.strip().str.title()

    before = len(df)
    df = df.dropna(subset=["order_date", "quantity", "product_id"])
    df = df[df["quantity"] > 0]
    stats["invalid_removed"] = before - len(df)

    df["quantity"] = df["quantity"].astype(int)
    df["product_id"] = df["product_id"].astype(int)
    df = df.merge(products, on="product_id", how="left")
    unmatched = int(df["unit_price"].isna().sum())
    df = df.dropna(subset=["unit_price"])
    stats["unmatched_products_removed"] = unmatched

    df["revenue"] = (df["quantity"] * df["unit_price"]).round(2)
    df["order_date"] = df["order_date"].dt.date
    stats["clean_rows"] = len(df)
    log.info("Cleaned orders: %s", stats)
    return df.reset_index(drop=True), stats
