import pytest
import requests

from pipeline import fetch


class FakeResponse:
    def __init__(self, data, status=200):
        self._data, self.status = data, status

    def raise_for_status(self):
        if self.status >= 400:
            raise requests.HTTPError(f"{self.status}")

    def json(self):
        return self._data


def test_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}
    waits = []

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.ConnectionError("temporary")
        return FakeResponse([{"id": 1, "title": "A", "price": 5, "category": "x"}])

    monkeypatch.setattr(requests, "get", flaky)
    frame, source = fetch.fetch_products(sleep=waits.append)
    assert source == "api" and len(frame) == 1
    assert calls["n"] == 3 and waits == [1.5, 3.0]  # exponential backoff


def test_falls_back_when_api_stays_down(api_down):
    frame, source = fetch.fetch_products(sleep=lambda s: None)
    assert source == "fallback" and len(frame) == 20
    assert list(frame.columns) == ["product_id", "product", "unit_price", "category"]


def test_bad_payload_triggers_fallback(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse({"oops": True}))
    _, source = fetch.fetch_products(sleep=lambda s: None)
    assert source == "fallback"


def test_with_retries_gives_up():
    def always():
        raise requests.Timeout("slow")

    with pytest.raises(requests.Timeout):
        fetch.with_retries(always, attempts=2, backoff=0, sleep=lambda s: None)
