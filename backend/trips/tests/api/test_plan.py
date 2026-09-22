"""``POST /api/trips/plan``: every error code in architecture.md section 4.4, plus the
``cycle_exhausted`` -> HTTP 200 path (implementation-plan.md's own Phase 3 exit criteria). Every
provider call is mocked/faked -- no real network, no ``ORS_API_KEY`` needed.
"""

import pytest
from rest_framework.test import APIClient

from trips.routing.base import (
    OutOfCoverageError,
    Place,
    Route,
    RouteLeg,
    UnroutableError,
    UpstreamError,
    UpstreamTimeoutError,
)
from trips.routing.geometry import encode_polyline

CURRENT = Place("Chicago, IL", 41.8781, -87.6298)
PICKUP = Place("St. Louis, MO", 38.6270, -90.1994)
DROPOFF = Place("Dallas, TX", 32.7767, -96.7970)
GEOMETRY = encode_polyline(
    [(41.8781, -87.6298), (40.0, -89.0), (38.6270, -90.1994), (35.0, -93.0), (32.7767, -96.7970)]
)

VALID_BODY = {
    "current_location": {"lat": CURRENT.lat, "lng": CURRENT.lng},
    "pickup_location": {"lat": PICKUP.lat, "lng": PICKUP.lng},
    "dropoff_location": {"lat": DROPOFF.lat, "lng": DROPOFF.lng},
    "cycle_used_hours": 0,
}


class _FakeRouting:
    def __init__(self, leg1_mi=100.0, leg2_mi=200.0):
        self.leg1_mi, self.leg2_mi = leg1_mi, leg2_mi

    def route(self, waypoints):
        legs = (
            RouteLeg(CURRENT, PICKUP, self.leg1_mi, ()),
            RouteLeg(PICKUP, DROPOFF, self.leg2_mi, ()),
        )
        return Route(
            GEOMETRY, ((32.7767, -96.7970), (41.8781, -87.6298)), legs, self.leg1_mi + self.leg2_mi
        )


class _FakeGeocoding:
    def search(self, query, *, limit=5):
        return [CURRENT]


class _RaisingRouting:
    def __init__(self, exc: Exception):
        self._exc = exc

    def route(self, waypoints):
        raise self._exc


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def _patch_adapters(monkeypatch, routing=None, geocoding=None) -> None:
    import trips.api.views as views_module

    monkeypatch.setattr(views_module, "_ors_adapter", lambda: routing or _FakeRouting())
    monkeypatch.setattr(views_module, "_photon_adapter", lambda: geocoding or _FakeGeocoding())


# --- the happy paths -----------------------------------------------------------------------------


def test_plan_returns_200_with_a_complete_trip(client, monkeypatch) -> None:
    _patch_adapters(monkeypatch)
    response = client.post("/api/trips/plan", VALID_BODY, format="json")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["status"] == "complete"
    assert body["summary"]["arrival_at"] is not None
    assert body["warnings"] == []
    assert set(body.keys()) == {
        "summary",
        "assumptions",
        "route",
        "stops",
        "daily_logs",
        "warnings",
    }


def test_plan_returns_200_with_cycle_exhausted_not_an_error(client, monkeypatch) -> None:
    """implementation-plan.md Phase 3 exit: "a cycle_exhausted request returns HTTP 200 with
    summary.status, the cycle_exhausted warning, unplanned and arrival_at = null"."""
    _patch_adapters(monkeypatch, routing=_FakeRouting(leg1_mi=50.0, leg2_mi=800.0))
    body = dict(VALID_BODY, cycle_used_hours=60)
    response = client.post("/api/trips/plan", body, format="json")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["status"] == "cycle_exhausted"
    assert data["summary"]["arrival_at"] is None
    assert data["summary"]["unplanned"] is not None
    assert any(w["code"] == "cycle_exhausted" for w in data["warnings"])


def test_plan_accepts_a_query_location(client, monkeypatch) -> None:
    _patch_adapters(monkeypatch)
    body = dict(VALID_BODY)
    body["current_location"] = {"query": "Chicago, IL"}
    response = client.post("/api/trips/plan", body, format="json")
    assert response.status_code == 200


# --- architecture.md section 4.4, one test per row ------------------------------------------------


def test_400_validation_error_missing_field(client) -> None:
    body = dict(VALID_BODY)
    del body["cycle_used_hours"]
    response = client.post("/api/trips/plan", body, format="json")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_400_validation_error_cycle_out_of_range(client) -> None:
    body = dict(VALID_BODY, cycle_used_hours=70.5)
    response = client.post("/api/trips/plan", body, format="json")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_400_validation_error_unknown_field(client) -> None:
    body = dict(VALID_BODY, unknown_field="nope")
    response = client.post("/api/trips/plan", body, format="json")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_400_validation_error_both_coords_and_query(client) -> None:
    body = dict(VALID_BODY)
    body["current_location"] = {"lat": 1.0, "lng": 1.0, "query": "Chicago"}
    response = client.post("/api/trips/plan", body, format="json")
    assert response.status_code == 400


def test_400_validation_error_outside_conus_bounds(client, monkeypatch) -> None:
    """services.py's own bounds check, surfaced through the same envelope."""
    _patch_adapters(monkeypatch)
    body = dict(VALID_BODY)
    body["current_location"] = {"lat": 61.2181, "lng": -149.9003}  # Anchorage, AK
    response = client.post("/api/trips/plan", body, format="json")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_422_unroutable(client, monkeypatch) -> None:
    _patch_adapters(monkeypatch, routing=_RaisingRouting(UnroutableError("no drivable route")))
    response = client.post("/api/trips/plan", VALID_BODY, format="json")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unroutable"


def test_422_out_of_coverage(client, monkeypatch) -> None:
    _patch_adapters(
        monkeypatch, routing=_RaisingRouting(OutOfCoverageError("route exceeds 6,000 km"))
    )
    response = client.post("/api/trips/plan", VALID_BODY, format="json")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "out_of_coverage"


def test_502_upstream_error(client, monkeypatch) -> None:
    _patch_adapters(monkeypatch, routing=_RaisingRouting(UpstreamError("ORS returned HTTP 500")))
    response = client.post("/api/trips/plan", VALID_BODY, format="json")
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_error"


def test_504_upstream_timeout(client, monkeypatch) -> None:
    _patch_adapters(
        monkeypatch, routing=_RaisingRouting(UpstreamTimeoutError("ORS did not respond"))
    )
    response = client.post("/api/trips/plan", VALID_BODY, format="json")
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "upstream_timeout"


def test_500_plan_self_check_failed(client, monkeypatch) -> None:
    """architecture.md AD-13: a validator disagreement is a 500, logged, never a silently-wrong
    plan returned to the client."""
    import trips.services as services_module
    from trips.hos.types import Violation, ViolationCode

    _patch_adapters(monkeypatch)
    monkeypatch.setattr(
        services_module,
        "hos_validate",
        lambda *a, **k: [Violation(ViolationCode.STATUS, None, "synthetic")],
    )
    response = client.post("/api/trips/plan", VALID_BODY, format="json")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "plan_self_check_failed"


def test_missing_ors_key_returns_a_clean_502_not_a_raw_traceback(client, monkeypatch) -> None:
    """R-ORS-LIVE: no key is available in this environment. Confirms that state produces the
    documented JSON envelope, not an HTML debug page (verified live in this environment already;
    this pins the behaviour as an automated regression test). Valid input + missing key -> 502."""
    monkeypatch.delenv("ORS_API_KEY", raising=False)
    response = client.post("/api/trips/plan", VALID_BODY, format="json")
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_error"


def test_out_of_conus_validation_is_not_masked_by_a_missing_ors_key(client, monkeypatch) -> None:
    """Phase 5 bug fix regression: PlanView used to build the routing adapter (_ors_adapter())
    before calling plan_trip(), so a missing/bad ORS_API_KEY raised before plan_trip() ever got a
    chance to run its own, provider-independent validation -- an out-of-CONUS location (a client
    mistake) came back as 502 upstream_error instead of the documented 400 validation_error. The
    routing adapter is now a lazy factory plan_trip() only calls once its own checks have passed,
    so invalid client input must win over provider unavailability, in either order."""
    monkeypatch.delenv("ORS_API_KEY", raising=False)
    body = dict(VALID_BODY)
    body["current_location"] = {"lat": 61.2181, "lng": -149.9003}  # Anchorage, AK
    response = client.post("/api/trips/plan", body, format="json")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


def test_405_on_get_is_reshaped_into_the_same_envelope(client) -> None:
    response = client.get("/api/trips/plan")
    assert response.status_code == 405
    assert "error" in response.json()
