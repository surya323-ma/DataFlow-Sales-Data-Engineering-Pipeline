import pytest
import requests

from pipeline import config, db


@pytest.fixture()
def engine(tmp_path):
    return db.get_engine(f"sqlite:///{tmp_path / 'test.db'}")


@pytest.fixture()
def api_down(monkeypatch):
    """Make every HTTP call fail so tests never touch the network."""
    def boom(*a, **k):
        raise requests.ConnectionError("network disabled in tests")
    monkeypatch.setattr(requests, "get", boom)


@pytest.fixture(autouse=True)
def no_email(monkeypatch):
    monkeypatch.setattr(config, "SMTP_HOST", "")
