"""``trips.services.plan_trip``: the composition layer, driven entirely by fakes (architecture.md
section 4.3: "Tests substitute fakes -- no network in unit tests"). Confirms the service layer
reshapes the HOS engine's own output faithfully rather than recomputing any of it.
"""

from datetime import UTC, datetime

import pytest

from trips.hos.types import PlanParams
from trips.routing.base import Place, Route, RouteLeg, UnroutableError
from trips.routing.geometry import encode_polyline
from trips.services import (
    LocationInput,
    PlanSelfCheckFailedError,
    TripInputError,
    TripPlanInputs,
    plan_trip,
)

CURRENT = Place("Chicago, IL", 41.8781, -87.6298)
PICKUP = Place("St. Louis, MO", 38.6270, -90.1994)
DROPOFF = Place("Dallas, TX", 32.7767, -96.7970)
NOW = datetime(2026, 9, 22, 6, 0, tzinfo=UTC)  # 01:00 America/Chicago -- still "today"

# S1's route shape (hos-rules.md section 11), mph=50: leg1=100mi, leg2=200mi.
_S1_POINTS = [
    (41.8781, -87.6298),
    (40.0, -88.5),
    (38.6270, -90.1994),
    (35.0, -93.0),
    (32.7767, -96.7970),
]
_S1_GEOMETRY = encode_polyline(_S1_POINTS)


class FakeRouting:
    def __init__(self, leg1_mi: float, leg2_mi: float, geometry: str = _S1_GEOMETRY):
        self.leg1_mi = leg1_mi
        self.leg2_mi = leg2_mi
        self.geometry = geometry

    def route(self, waypoints):
        legs = (
            RouteLeg(CURRENT, PICKUP, self.leg1_mi, ()),
            RouteLeg(PICKUP, DROPOFF, self.leg2_mi, ()),
        )
        return Route(
            geometry=self.geometry,
            bounds=((32.7767, -96.7970), (41.8781, -87.6298)),
            legs=legs,
            distance_mi=self.leg1_mi + self.leg2_mi,
        )


class UnroutableRouting:
    def route(self, waypoints):
        raise UnroutableError("no drivable route between the given points")


class FakeGeocoding:
    def __init__(self, hit: Place = CURRENT):
        self.hit = hit
        self.calls: list[str] = []

    def search(self, query, *, limit=5):
        self.calls.append(query)
        return [self.hit] if query else []


def _inputs(cycle_used_hours: float = 0.0) -> TripPlanInputs:
    return TripPlanInputs(
        current_location=LocationInput(CURRENT.label, CURRENT.lat, CURRENT.lng, None),
        pickup_location=LocationInput(PICKUP.label, PICKUP.lat, PICKUP.lng, None),
        dropoff_location=LocationInput(DROPOFF.label, DROPOFF.lat, DROPOFF.lng, None),
        cycle_used_hours=cycle_used_hours,
    )


PARAMS_MPH50 = PlanParams(avg_speed_mph=50)


def test_s1_shape_produces_a_complete_plan_with_matching_totals() -> None:
    """S1's own numbers (hos-rules.md section 11): driving 6h, on-duty-not-driving 2.25h."""
    result = plan_trip(
        _inputs(0.0),
        routing=lambda: FakeRouting(100.0, 200.0),
        geocoding=FakeGeocoding(),
        params=PARAMS_MPH50,
        now=NOW,
    )
    assert result["summary"]["status"] == "complete"
    assert result["summary"]["total_driving_hours"] == pytest.approx(6.0)
    assert result["summary"]["total_on_duty_hours"] == pytest.approx(8.25)
    assert result["summary"]["arrival_at"] is not None
    assert result["summary"]["unplanned"] is None
    assert result["warnings"] == []
    assert len(result["daily_logs"]) == 1
    assert sum(result["daily_logs"][0]["totals_h"].values()) == pytest.approx(24.0)


def test_cycle_exhausted_shape_matches_s4() -> None:
    """S4's numbers (hos-rules.md section 11): cycle 60h, legs 50/800mi -> stop at mile 437.5."""
    result = plan_trip(
        _inputs(60.0),
        routing=lambda: FakeRouting(
            50.0, 800.0, geometry=encode_polyline([CURRENT_LL, (32.7767, -96.7970)])
        ),
        geocoding=FakeGeocoding(),
        params=PARAMS_MPH50,
        now=NOW,
    )
    assert result["summary"]["status"] == "cycle_exhausted"
    assert result["summary"]["arrival_at"] is None
    assert result["summary"]["unplanned"]["miles"] == pytest.approx(412.5)
    assert result["summary"]["unplanned"]["blocked"] == "drive"
    assert result["summary"]["unplanned"]["pending"] == ["dropoff"]
    assert result["summary"]["cycle"]["status"] == "exhausted"
    assert len(result["warnings"]) == 1
    assert result["warnings"][0]["code"] == "cycle_exhausted"
    assert result["warnings"][0]["details"]["shortfall_min"] == 555
    assert any(s["type"] == "cycle_limit" for s in result["stops"])


CURRENT_LL = (41.8781, -87.6298)


def test_query_location_resolves_via_geocoding() -> None:
    geocoding = FakeGeocoding(hit=PICKUP)
    inputs = TripPlanInputs(
        current_location=LocationInput(None, None, None, "St. Louis, MO"),
        pickup_location=LocationInput(PICKUP.label, PICKUP.lat, PICKUP.lng, None),
        dropoff_location=LocationInput(DROPOFF.label, DROPOFF.lat, DROPOFF.lng, None),
        cycle_used_hours=0.0,
    )
    result = plan_trip(
        inputs,
        routing=lambda: FakeRouting(0.0, 200.0),
        geocoding=geocoding,
        params=PARAMS_MPH50,
        now=NOW,
    )
    assert geocoding.calls == ["St. Louis, MO"]
    assert result["route"]["legs"][0]["from"]["label"] == PICKUP.label


def test_query_with_no_geocoding_hits_raises_trip_input_error() -> None:
    with pytest.raises(TripInputError):
        plan_trip(
            TripPlanInputs(
                current_location=LocationInput(None, None, None, ""),
                pickup_location=LocationInput(PICKUP.label, PICKUP.lat, PICKUP.lng, None),
                dropoff_location=LocationInput(DROPOFF.label, DROPOFF.lat, DROPOFF.lng, None),
                cycle_used_hours=0.0,
            ),
            routing=lambda: FakeRouting(100.0, 200.0),
            geocoding=FakeGeocoding(hit=CURRENT),
            now=NOW,
        )


@pytest.mark.parametrize("lat,lng", [(61.2181, -149.9003), (55.0, -100.0), (40.0, -40.0)])
def test_out_of_conus_bounds_raises_trip_input_error(lat: float, lng: float) -> None:
    inputs = TripPlanInputs(
        current_location=LocationInput("Outside", lat, lng, None),
        pickup_location=LocationInput(PICKUP.label, PICKUP.lat, PICKUP.lng, None),
        dropoff_location=LocationInput(DROPOFF.label, DROPOFF.lat, DROPOFF.lng, None),
        cycle_used_hours=0.0,
    )
    with pytest.raises(TripInputError, match="contiguous US"):
        plan_trip(
            inputs, routing=lambda: FakeRouting(100.0, 200.0), geocoding=FakeGeocoding(), now=NOW
        )


def test_cycle_used_hours_above_70_raises_trip_input_error() -> None:
    with pytest.raises(TripInputError):
        plan_trip(
            _inputs(70.01),
            routing=lambda: FakeRouting(100.0, 200.0),
            geocoding=FakeGeocoding(),
            now=NOW,
        )


def test_routing_provider_failure_propagates_as_the_typed_error() -> None:
    """services.py does not catch or hide a provider failure -- the API layer's exception handler
    is what turns this into the JSON envelope (architecture.md section 4.4)."""
    with pytest.raises(UnroutableError):
        plan_trip(
            _inputs(0.0), routing=lambda: UnroutableRouting(), geocoding=FakeGeocoding(), now=NOW
        )


def test_self_check_failure_is_raised_when_the_validator_disagrees(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If hos.validate ever disagreed with hos.plan, services.py must refuse to return the plan --
    architecture.md AD-13 / section 4.4: HTTP 500 plan_self_check_failed, never a wrong plan."""
    import trips.services as services_module
    from trips.hos.types import Violation, ViolationCode

    def fake_validate(*args, **kwargs):
        return [Violation(ViolationCode.STATUS, None, "synthetic failure for this test")]

    monkeypatch.setattr(services_module, "hos_validate", fake_validate)
    with pytest.raises(PlanSelfCheckFailedError) as exc_info:
        plan_trip(
            _inputs(0.0),
            routing=lambda: FakeRouting(100.0, 200.0),
            geocoding=FakeGeocoding(),
            now=NOW,
        )
    assert len(exc_info.value.violations) == 1


def test_response_never_duplicates_hos_logic_it_only_reshapes_it() -> None:
    """The response's per-day totals must come from the exact same HOS totals every other Phase 1
    test already checked -- not a second, re-derived computation (AD-2's "one implementation")."""
    from trips.hos.logs import build_daily_logs
    from trips.hos.planner import plan as hos_plan

    direct = hos_plan(100.0, 200.0, 0, 8 * 60, PARAMS_MPH50)
    direct_logs = build_daily_logs(direct)

    result = plan_trip(
        _inputs(0.0),
        routing=lambda: FakeRouting(100.0, 200.0),
        geocoding=FakeGeocoding(),
        params=PARAMS_MPH50,
        now=NOW,
    )

    assert len(result["daily_logs"]) == len(direct_logs)
    for api_log, direct_log in zip(result["daily_logs"], direct_logs, strict=True):
        assert api_log["totals_h"]["D"] == pytest.approx(direct_log.totals.d / 60)
        assert api_log["totals_h"]["ON"] == pytest.approx(direct_log.totals.on / 60)
        assert api_log["recap"]["a_last_8_days_h"] == pytest.approx(
            direct_log.recap.cycle_used_min / 60
        )


def test_deterministic_given_the_same_now() -> None:
    a = plan_trip(
        _inputs(0.0),
        routing=lambda: FakeRouting(100.0, 200.0),
        geocoding=FakeGeocoding(),
        params=PARAMS_MPH50,
        now=NOW,
    )
    b = plan_trip(
        _inputs(0.0),
        routing=lambda: FakeRouting(100.0, 200.0),
        geocoding=FakeGeocoding(),
        params=PARAMS_MPH50,
        now=NOW,
    )
    assert a == b


def test_stop_ids_are_sequential_and_route_mile_is_non_decreasing() -> None:
    result = plan_trip(
        _inputs(0.0),
        routing=lambda: FakeRouting(100.0, 200.0),
        geocoding=FakeGeocoding(),
        params=PARAMS_MPH50,
        now=NOW,
    )
    ids = [s["id"] for s in result["stops"]]
    assert ids == [f"s{i}" for i in range(len(ids))]
    miles = [s["route_mile"] for s in result["stops"]]
    assert miles == sorted(miles)


def test_departure_local_time_is_always_08_00_a16() -> None:
    result = plan_trip(
        _inputs(0.0),
        routing=lambda: FakeRouting(100.0, 200.0),
        geocoding=FakeGeocoding(),
        params=PARAMS_MPH50,
        now=NOW,
    )
    assert result["assumptions"]["departure_local_time"] == "08:00"
    assert result["summary"]["departure_at"].endswith("T08:00:00-05:00")
