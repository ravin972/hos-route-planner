"""``PlanParams`` input validation and basic dataclass behaviour."""

import pytest

from trips.hos.types import Kind, PlanParams, Segment, Status


def test_defaults_match_the_documented_assumptions() -> None:
    params = PlanParams()
    assert params.avg_speed_mph == 55
    assert params.pretrip_min == 15
    assert params.pickup_min == 60
    assert params.dropoff_min == 60
    assert params.fuel_stop_min == 30
    assert params.fuel_interval_miles == 1000
    assert params.allow_34_hour_restart is False


def test_params_are_frozen() -> None:
    params = PlanParams()
    with pytest.raises(AttributeError):
        params.avg_speed_mph = 60  # type: ignore[misc]


@pytest.mark.parametrize("bad_speed", [0, -1, 80.01, float("inf"), float("nan")])
def test_avg_speed_mph_out_of_range_is_refused(bad_speed: float) -> None:
    with pytest.raises(ValueError):
        PlanParams(avg_speed_mph=bad_speed)


def test_avg_speed_mph_wrong_type_is_refused() -> None:
    with pytest.raises(TypeError):
        PlanParams(avg_speed_mph="55")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        PlanParams(avg_speed_mph=True)  # bool is not a speed


@pytest.mark.parametrize("field", ["pretrip_min", "pickup_min", "dropoff_min", "fuel_stop_min"])
def test_duration_fields_reject_non_int_minutes(field: str) -> None:
    with pytest.raises(TypeError):
        PlanParams(**{field: 15.0})
    with pytest.raises(TypeError):
        PlanParams(**{field: True})


@pytest.mark.parametrize("field", ["pretrip_min", "pickup_min", "dropoff_min", "fuel_stop_min"])
def test_duration_fields_reject_non_positive_minutes(field: str) -> None:
    with pytest.raises(ValueError):
        PlanParams(**{field: 0})
    with pytest.raises(ValueError):
        PlanParams(**{field: -5})


def test_allow_34_hour_restart_must_be_a_bool() -> None:
    with pytest.raises(TypeError):
        PlanParams(allow_34_hour_restart=1)  # type: ignore[arg-type]


def test_pretrip_plus_longest_on_duty_stop_must_fit_one_cycle() -> None:
    with pytest.raises(ValueError):
        PlanParams(pretrip_min=4185, dropoff_min=16)  # 4185 + 16 = 4201 > 4200


def test_segment_minutes_and_miles_properties() -> None:
    seg = Segment(360, 375, Status.ON, Kind.PRETRIP, 10.0, 10.0)
    assert seg.minutes == 15
    assert seg.miles == 0.0

    drive = Segment(375, 435, Status.D, Kind.DRIVE, 10.0, 60.0)
    assert drive.minutes == 60
    assert drive.miles == 50.0
