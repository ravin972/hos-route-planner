"""Boundary cases from hos-rules.md section 11 ("Boundary cases" list) that exercise the planner
directly: exact-limit cycle inputs, the atomic-activity edge, structural edges (0-mile legs,
midnight, departure at 23:50), and the restart option applied to the same boundaries.
"""

import pytest

from trips.hos.planner import plan
from trips.hos.types import Blocked, Kind, PlanParams, PlanStatus, Status
from trips.hos.validator import validate

PARAMS = PlanParams(avg_speed_mph=50)
PARAMS_RESTART = PlanParams(avg_speed_mph=50, allow_34_hour_restart=True)


def hm(hours: int, minutes: int = 0) -> int:
    return hours * 60 + minutes


def assert_clean(result, carry_in: int, params: PlanParams = PARAMS) -> None:
    """Every produced plan -- complete or truncated -- must validate clean (property 1)."""
    assert validate(result.segments, carry_in, params, result.departure) == []


# --- cycle boundaries -------------------------------------------------------------------------


def test_cycle_used_exactly_70_schedules_nothing() -> None:
    result = plan(100, 200, hm(70), hm(6), PARAMS)
    assert result.status == PlanStatus.CYCLE_EXHAUSTED
    assert result.segments == ()
    assert result.stop.blocked == Blocked.PRETRIP
    assert_clean(result, hm(70))


def test_cycle_used_69_75_pretrip_fits_exactly_then_blocked_drive() -> None:
    result = plan(100, 200, hm(69, 45), hm(6), PARAMS)  # R = 15
    assert result.status == PlanStatus.CYCLE_EXHAUSTED
    assert len(result.segments) == 1
    assert result.segments[0].kind == Kind.PRETRIP
    assert result.stop.blocked == Blocked.DRIVE
    assert_clean(result, hm(69, 45))


def test_cycle_used_above_70_is_rejected_by_plan() -> None:
    with pytest.raises(ValueError):
        plan(100, 200, 4201, hm(6), PARAMS)  # 70.01 h -> 400 validation_error at the API layer


def test_cycle_used_69_999h_rounds_to_4200_min_at_the_service_boundary() -> None:
    """rule M-1: conversion happens once, at the API/service boundary (round half up), never
    here. ``plan()`` itself only accepts an already-integer minute count -- this documents that."""
    from math import floor

    minutes = floor(69.999 * 60 + 0.5)
    assert minutes == 4200
    result = plan(100, 200, minutes, hm(6), PARAMS)
    assert result.status == PlanStatus.CYCLE_EXHAUSTED
    assert_clean(result, minutes)


def test_exactly_exhausted_by_the_final_dropoff_is_complete() -> None:
    """S1's own cycle consumption is 8.25 h; starting with exactly 70 - 8.25 h carried in should
    still complete, landing at cycle == 4200 with nothing left over."""
    carry_in = hm(70) - int(8.25 * 60)
    result = plan(100, 200, carry_in, hm(6), PARAMS)
    assert result.status == PlanStatus.COMPLETE
    assert result.stop is None
    final_cycle = carry_in + sum(s.minutes for s in result.segments if s.status in ("D", "ON"))
    assert final_cycle == 4200
    assert_clean(result, carry_in)


def test_dropoff_blocked_with_r_59_complete_with_r_60() -> None:
    # From S1's shape: after pickup, driving to the dropoff milestone leaves R = base - drive.
    # Pick a carry-in so that R is exactly 59 at the moment the 60-min dropoff is attempted.
    # S1's consumption up to (but not including) the dropoff is 15+120+60+240 = 435 min.
    carry_in_blocked = hm(70) - 435 - 59
    result = plan(100, 200, carry_in_blocked, hm(6), PARAMS)
    assert result.status == PlanStatus.CYCLE_EXHAUSTED
    assert result.stop.blocked == Blocked.DROPOFF
    assert_clean(result, carry_in_blocked)

    carry_in_complete = hm(70) - 435 - 60
    result2 = plan(100, 200, carry_in_complete, hm(6), PARAMS)
    assert result2.status == PlanStatus.COMPLETE
    assert_clean(result2, carry_in_complete)


def test_fuel_due_blocked_with_r_29_fuel_then_wall_with_r_30() -> None:
    """S3's own route (leg1=100, leg2=1000) reaches the 1,000-mile fuel point on day 2, after a
    rest -- 1,000 mi cannot be driven in a single 11 h shift (550 mi), so at least one rest is
    unavoidable before fuel is ever due. The exact on-duty consumption up to that point is derived
    from a zero-carry-in baseline run rather than hand-computed, since a naive single-shift
    estimate is wrong here (as an earlier, incorrect version of this test discovered)."""
    baseline = plan(100, 1000, 0, hm(6), PARAMS)
    fuel_index = next(i for i, s in enumerate(baseline.segments) if s.kind == Kind.FUEL)
    consumption_to_fuel_point = sum(
        s.minutes for s in baseline.segments[:fuel_index] if s.status in (Status.D, Status.ON)
    )

    carry_in_blocked = 4200 - consumption_to_fuel_point - 29
    result = plan(100, 1000, carry_in_blocked, hm(6), PARAMS)
    assert result.status == PlanStatus.CYCLE_EXHAUSTED
    assert result.stop.blocked == Blocked.FUEL
    assert_clean(result, carry_in_blocked)

    carry_in_wall = 4200 - consumption_to_fuel_point - 30
    result2 = plan(100, 1000, carry_in_wall, hm(6), PARAMS)
    assert result2.status == PlanStatus.CYCLE_EXHAUSTED
    assert result2.stop.blocked == Blocked.DRIVE  # fuel is scheduled, then the wall hits next
    assert any(s.kind == Kind.FUEL for s in result2.segments)
    assert_clean(result2, carry_in_wall)


def test_11h_limit_reached_r15_next_shift_r16_rests() -> None:
    # A long single leg so the 11 h driving limit binds before the milestone is reached.
    consumption_to_limit = 15 + 660  # pretrip + a full 11 h driving shift
    carry_in_next_shift = hm(70) - consumption_to_limit - 15
    result = plan(3000, 1, carry_in_next_shift, hm(6), PARAMS)
    assert result.status == PlanStatus.CYCLE_EXHAUSTED
    assert result.stop.blocked == Blocked.NEXT_SHIFT
    assert not any(s.kind == Kind.REST for s in result.segments)
    assert_clean(result, carry_in_next_shift)

    carry_in_rest = hm(70) - consumption_to_limit - 16
    result2 = plan(3000, 1, carry_in_rest, hm(6), PARAMS)
    assert any(s.kind == Kind.REST for s in result2.segments)
    # after the rest: a fresh pre-trip, then at least 1 more minute of driving
    rest_index = next(i for i, s in enumerate(result2.segments) if s.kind == Kind.REST)
    assert result2.segments[rest_index + 1].kind == Kind.PRETRIP
    assert result2.segments[rest_index + 2].status == Status.D
    assert_clean(result2, carry_in_rest)


@pytest.mark.parametrize(
    "carry_in",
    [
        hm(70),
        hm(69, 45),
        hm(70) - 435 - 59,
    ],
)
def test_every_no_restart_boundary_also_restarts_when_the_option_is_on(carry_in: int) -> None:
    """hos-rules.md section 11: "each of these again with the restart option on -> restart
    inserted." With the option on, the same inputs that stopped above must instead complete."""
    result = plan(100, 200, carry_in, hm(6), PARAMS_RESTART)
    assert result.status == PlanStatus.COMPLETE
    assert any(s.kind == Kind.RESTART for s in result.segments)
    assert_clean(result, carry_in, PARAMS_RESTART)


# --- structure and inputs ---------------------------------------------------------------------


def test_zero_mile_leg1_pickup_equals_current_location() -> None:
    result = plan(0, 200, 0, hm(6), PARAMS)
    assert result.status == PlanStatus.COMPLETE
    assert result.segments[0].kind == Kind.PRETRIP
    assert result.segments[1].kind == Kind.PICKUP  # no drive segment before it
    assert result.segments[1].pos_start == 0.0
    assert_clean(result, 0)


def test_zero_mile_leg2_pickup_equals_dropoff_location() -> None:
    result = plan(100, 0, 0, hm(6), PARAMS)
    assert result.status == PlanStatus.COMPLETE
    kinds = [s.kind for s in result.segments]
    assert kinds.index(Kind.PICKUP) + 1 == kinds.index(Kind.DROPOFF)  # back to back, no drive
    assert_clean(result, 0)


def test_both_legs_zero_miles_is_legal() -> None:
    result = plan(0, 0, 0, hm(6), PARAMS)
    assert result.status == PlanStatus.COMPLETE
    assert [s.kind for s in result.segments] == [Kind.PRETRIP, Kind.PICKUP, Kind.DROPOFF]
    assert_clean(result, 0)


def test_segment_can_end_exactly_at_24_00() -> None:
    # 23:45 departure + a 15-min pre-trip ends at exactly minute 1,440 (midnight) -- the pre-trip
    # segment itself, regardless of what the rest of the trip goes on to do.
    result = plan(100, 200, 0, hm(23, 45), PARAMS)
    assert result.segments[0].start == hm(23, 45)
    assert result.segments[0].kind == Kind.PRETRIP
    assert result.segments[0].end == 24 * 60  # midnight, exactly
    assert_clean(result, 0)


def test_departure_at_23_50_crosses_midnight_immediately() -> None:
    result = plan(50, 50, 0, hm(23, 50), PARAMS)
    assert result.segments[0].start == hm(23, 50)
    assert result.segments[0].end == 24 * 60 + 5  # pretrip crosses midnight
    assert_clean(result, 0)


def test_every_segment_boundary_is_an_int() -> None:
    result = plan(137.5, 941.25, 1234, hm(6, 17), PARAMS)
    for seg in result.segments:
        assert type(seg.start) is int
        assert type(seg.end) is int
    assert_clean(result, 1234)


# --- input validation --------------------------------------------------------------------------


def test_plan_rejects_a_float_cycle_used_min() -> None:
    with pytest.raises((TypeError, ValueError)):
        plan(100, 200, 100.0, hm(6), PARAMS)  # type: ignore[arg-type]


def test_plan_rejects_a_negative_leg() -> None:
    with pytest.raises(ValueError):
        plan(-1, 200, 0, hm(6), PARAMS)


def test_plan_rejects_a_non_planparams_params_argument() -> None:
    with pytest.raises(TypeError):
        plan(100, 200, 0, hm(6), object())  # type: ignore[arg-type]
