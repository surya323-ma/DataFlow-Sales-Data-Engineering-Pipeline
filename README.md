# DataFlow – Sales Data Engineering Pipeline

Automated ETL pipeline: **fetch** product data from an API and orders from a CSV, **clean** them with Pandas, **load** them into a SQL database, then **email a scheduled summary report**. A small dashboard shows run history and the latest report.

**Stack:** Python 3.12 · Pandas · SQLAlchemy (SQLite / PostgreSQL) · Requests · FastAPI dashboard · cron · pytest

## What it does
1. **Extract:** `pipeline/fetch.py` calls the products API with timeout, exponential-backoff retries and a bundled fallback snapshot if the API stays down. Orders come from `data/orders.csv`.
2. **Transform:** `pipeline/clean.py` removes duplicate order ids, bad dates and non-positive quantities, normalises names and regions, joins product prices and computes revenue. It returns data-quality counts for the report footer.
3. **Load:** `pipeline/db.py` writes `orders_clean` and `products` tables (replace-per-run, so reruns never duplicate) and records every run in `pipeline_runs`.
4. **Report:** `pipeline/report.py` builds revenue, top products, category and region breakdowns, and flags unusual days with an IQR (Tukey) rule. Output is email-safe inline HTML.
5. **Notify:** `pipeline/notify.py` emails the report over SMTP when configured. A mail failure never fails the run.
6. **Observe:** structured logging, per-run duration and status, error text on failure. The dashboard shows it all.

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pipeline.run                    # one pipeline run
uvicorn web.app:app --reload              # dashboard at http://localhost:8000
pytest                                    # 17 tests, ~93% coverage, no network needed
```

## Schedule it
- **Server / VM:** see `crontab.example`.
- **Render:** `render.yaml` defines a cron job (daily 02:00 UTC). Render cron jobs are a paid instance type; check current pricing.
- **No paid cron?** Use a free scheduler such as cron-job.org to call `POST https://<your-app>.onrender.com/api/run` with header `X-Run-Token: <RUN_TOKEN>`.

## Deploy to Render
1. Push to GitHub.
2. Render → **New → Blueprint** → select the repo.
3. Set `RUN_TOKEN` (and optionally the `SMTP_*` / `REPORT_TO` variables) when prompted.
4. Open the dashboard URL and press **Run pipeline now**.

> The free web service sleeps when idle and free Postgres databases expire after a limited period; check Render's current terms.

## Using your own data
Replace `data/orders.csv` (columns: `order_id, order_date, customer, product_id, quantity, region`) or point `ORDERS_CSV` and `PRODUCTS_API_URL` at your own sources.

## Measuring the time saved
Each run stores `duration_s`. Compare it with how long the manual version took, for example *"Cut a daily 2-hour manual report to under 1 minute"*, and put your real numbers on your resume.
