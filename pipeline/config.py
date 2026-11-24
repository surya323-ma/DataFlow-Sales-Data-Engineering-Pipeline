import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'pipeline.db'}")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

ORDERS_CSV = Path(os.getenv("ORDERS_CSV", BASE_DIR / "data" / "orders.csv"))
PRODUCTS_FALLBACK = BASE_DIR / "data" / "products_fallback.json"
PRODUCTS_API_URL = os.getenv("PRODUCTS_API_URL", "https://fakestoreapi.com/products")

HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "10"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
BACKOFF_SECONDS = float(os.getenv("BACKOFF_SECONDS", "1.5"))

# Email is optional: without SMTP_HOST the report is stored in the database only.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
REPORT_FROM = os.getenv("REPORT_FROM", SMTP_USER or "reports@example.com")
REPORT_TO = [a.strip() for a in os.getenv("REPORT_TO", "").split(",") if a.strip()]

RUN_TOKEN = os.getenv("RUN_TOKEN", "")  # if set, POST /run from the dashboard must send it
