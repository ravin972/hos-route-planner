"""``GET /api/locations/search`` (architecture.md AD-6). Photon is faked -- no real network."""

import pytest
from rest_framework.test import APIClient

from trips.routing.base import Place, UpstreamError, UpstreamTimeoutError


class _FakeGeocoding:
    def __init__(self, results=None):
        self._results = (
            results if results is not None else [Place("Chicago, IL", 41.8781, -87.6298)]
        )
        self.last_query = None
        self.last_limit = None

    def search(self, query, *, limit=5):
        self.last_query, self.last_limit = query, limit
        return self._results


class _RaisingGeocoding:
    def __init__(self, exc: Exception):
        self._exc = exc

    def search(self, query, *, limit=5):
        raise self._exc


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def _patch(monkeypatch, geocoding) -> None:
    import trips.api.views as views_module

    monkeypatch.setattr(views_module, "_photon_adapter", lambda: geocoding)


def test_search_returns_results(client, monkeypatch) -> None:
    fake = _FakeGeocoding()
    _patch(monkeypatch, fake)
    response = client.get("/api/locations/search", {"q": "Chicago"})
    assert response.status_code == 200
    body = response.json()
    assert body == {"results": [{"label": "Chicago, IL", "lat": 41.8781, "lng": -87.6298}]}
    assert fake.last_query == "Chicago"
    assert fake.last_limit == 5


def test_search_passes_through_a_custom_limit(client, monkeypatch) -> None:
    fake = _FakeGeocoding()
    _patch(monkeypatch, fake)
    client.get("/api/locations/search", {"q": "Chicago", "limit": 3})
    assert fake.last_limit == 3


def test_search_requires_q(client) -> None:
    response = client.get("/api/locations/search")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_search_rejects_limit_over_20(client) -> None:
    response = client.get("/api/locations/search", {"q": "Chicago", "limit": 21})
    assert response.status_code == 400


def test_search_upstream_error_is_mapped(client, monkeypatch) -> None:
    _patch(monkeypatch, _RaisingGeocoding(UpstreamError("Photon returned HTTP 500")))
    response = client.get("/api/locations/search", {"q": "Chicago"})
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_error"


def test_search_upstream_timeout_is_mapped(client, monkeypatch) -> None:
    _patch(monkeypatch, _RaisingGeocoding(UpstreamTimeoutError("Photon did not respond")))
    response = client.get("/api/locations/search", {"q": "Chicago"})
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "upstream_timeout"


def test_search_empty_results_is_still_200(client, monkeypatch) -> None:
    _patch(monkeypatch, _FakeGeocoding(results=[]))
    response = client.get("/api/locations/search", {"q": "xyzzy-not-a-place"})
    assert response.status_code == 200
    assert response.json() == {"results": []}
