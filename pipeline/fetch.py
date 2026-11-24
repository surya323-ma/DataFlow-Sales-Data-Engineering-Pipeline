"""Extract step: pull product data from an API and order data from a CSV file."""
import json
import time

import pandas as pd
import requests

from . import config
from .logging_setup import get_logger

log = get_logger("pipeline.fetch")


def with_retries(func, *, attempts: int | None = None, backoff: float | None = None, sleep=time.sleep):
    """Call func(); on failure wait backoff * 2**n seconds and try again."""
    attempts = attempts or config.MAX_RETRIES
    backoff = config.BACKOFF_SECONDS if backoff is None else backoff
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except (requests.RequestException, ValueError) as exc:
            if attempt == attempts:
                raise
            wait = backoff * 2 ** (attempt - 1)
            log.warning("Attempt %d/%d failed (%s). Retrying in %.1fs", attempt, attempts, exc, wait)
            sleep(wait)


def fetch_products(url: str | None = None, sleep=time.sleep) -> tuple[pd.DataFrame, str]:
    """Return (products, source). Falls back to a bundled snapshot if the API stays down."""
    url = url or config.PRODUCTS_API_URL

    def call():
        response = requests.get(url, timeout=config.HTTP_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list) or not data:
            raise ValueError("API returned no products")
        return data

    try:
        data = with_retries(call, sleep=sleep)
        source = "api"
        log.info("Fetched %d products from %s", len(data), url)
    except (requests.RequestException, ValueError) as exc:
        log.error("API unavailable after retries (%s). Using bundled snapshot.", exc)
        data = json.loads(config.PRODUCTS_FALLBACK.read_text())
        source = "fallback"
    frame = pd.DataFrame(data)[["id", "title", "price", "category"]]
    return frame.rename(columns={"id": "product_id", "title": "product", "price": "unit_price"}), source


def read_orders(path=None) -> pd.DataFrame:
    path = path or config.ORDERS_CSV
    frame = pd.read_csv(path, dtype=str)
    log.info("Read %d raw order rows from %s", len(frame), path)
    return frame
