"""Load step and run history."""
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String, Table, Text, create_engine, desc, select

from . import config

metadata = MetaData()
runs = Table(
    "pipeline_runs", metadata,
    Column("id", Integer, primary_key=True),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
    Column("status", String(12)),
    Column("source", String(12)),
    Column("rows_loaded", Integer),
    Column("duration_s", Float),
    Column("emailed", Integer, default=0),
    Column("error", Text),
    Column("report_html", Text),
)


def get_engine(url: str | None = None):
    url = url or config.DATABASE_URL
    args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=args, pool_pre_ping=True)
    metadata.create_all(engine)
    return engine


def load_orders(engine, orders: pd.DataFrame, products: pd.DataFrame) -> int:
    """Replace the warehouse tables with the freshly cleaned data (idempotent per run)."""
    orders.to_sql("orders_clean", engine, if_exists="replace", index=False)
    products.to_sql("products", engine, if_exists="replace", index=False)
    return len(orders)


def start_run(engine) -> int:
    with engine.begin() as conn:
        result = conn.execute(runs.insert().values(started_at=datetime.now(timezone.utc), status="running"))
        return result.inserted_primary_key[0]


def finish_run(engine, run_id: int, **values) -> None:
    with engine.begin() as conn:
        conn.execute(runs.update().where(runs.c.id == run_id).values(finished_at=datetime.now(timezone.utc), **values))


def recent_runs(engine, limit: int = 10) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(select(runs).order_by(desc(runs.c.id)).limit(limit)).mappings().all()
    return [dict(r) for r in rows]


def latest_report(engine) -> str | None:
    with engine.connect() as conn:
        return conn.execute(
            select(runs.c.report_html).where(runs.c.status == "success").order_by(desc(runs.c.id)).limit(1)
        ).scalar()
