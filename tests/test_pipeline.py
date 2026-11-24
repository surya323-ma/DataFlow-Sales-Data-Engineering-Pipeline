from fastapi.testclient import TestClient

from pipeline import config, db, notify
from pipeline.run import run_pipeline
from web import app as web_app


def test_full_run_with_fallback_data(engine, api_down):
    result = run_pipeline(engine, sleep=lambda s: None)
    assert result["status"] == "success" and result["rows"] > 200

    runs = db.recent_runs(engine)
    assert runs[0]["status"] == "success" and runs[0]["source"] == "fallback"
    assert "Daily sales summary" in db.latest_report(engine)


def test_rerun_does_not_duplicate_rows(engine, api_down):
    first = run_pipeline(engine, sleep=lambda s: None)
    second = run_pipeline(engine, sleep=lambda s: None)
    assert first["rows"] == second["rows"]
    with engine.connect() as conn:
        count = conn.exec_driver_sql("select count(*) from orders_clean").scalar()
    assert count == second["rows"]


def test_failed_run_is_recorded(engine, api_down, monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ORDERS_CSV", tmp_path / "missing.csv")
    result = run_pipeline(engine, sleep=lambda s: None)
    assert result["status"] == "failed"
    assert db.recent_runs(engine)[0]["status"] == "failed"
    assert db.latest_report(engine) is None


def test_email_failure_does_not_fail_run(engine, api_down, monkeypatch):
    monkeypatch.setattr(notify, "send_report", lambda *a: (_ for _ in ()).throw(RuntimeError("smtp down")))
    assert run_pipeline(engine, sleep=lambda s: None)["status"] == "success"


def test_dashboard_api(engine, api_down, monkeypatch):
    monkeypatch.setattr(web_app, "_engine", engine)
    client = TestClient(web_app.app)
    assert client.get("/api/report/latest").status_code == 404
    assert client.get("/").status_code == 200

    res = client.post("/api/run")
    assert res.status_code == 200 and res.json()["status"] == "success"
    assert "Daily sales summary" in client.get("/api/report/latest").text
    runs = client.get("/api/runs").json()
    assert runs["runs"][0]["status"] == "success" and "report_html" not in runs["runs"][0]


def test_run_token_protects_trigger(engine, monkeypatch):
    monkeypatch.setattr(web_app, "_engine", engine)
    monkeypatch.setattr(config, "RUN_TOKEN", "secret")
    client = TestClient(web_app.app)
    assert client.post("/api/run").status_code == 401
