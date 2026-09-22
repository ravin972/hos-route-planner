"""Golden scenarios S1-S6 and S4b: the hand-computed oracles in hos-rules.md section 11.

Every scenario checks the full segment timeline against the table (times, status, kind, mileage),
the per-day totals and recap, that ``validate()`` returns no violations, and -- for a truncated
plan -- every ``CycleStop`` field. ``mph = 50`` throughout, matching the doc's choice so every
limit lands on a whole minute.
"""

from trips.hos.logs import build_daily_logs
from trips.hos.planner import plan
from trips.hos.types import Blocked, Kind, PlanParams, PlanStatus, Status
from trips.hos.validator import validate

PARAMS = PlanParams(avg_speed_mph=50)
PARAMS_RESTART = PlanParams(avg_speed_mph=50, allow_34_hour_restart=True)


def hm(hours: int, minutes: int = 0) -> int:
    """``hh:mm`` on day 1 (minutes since midnight)."""
    return hours * 60 + minutes


def assert_timeline(segments, expected: list[tuple[int, int, Status, Kind]]) -> None:
    actual = [(s.start, s.end, s.status, s.kind) for s in segments]
    assert actual == expected


def assert_totals(totals, off: float, sb: float, d: float, on: float) -> None:
    assert totals.off / 60 == off
    assert totals.sb / 60 == sb
    assert totals.d / 60 == d
    assert totals.on / 60 == on
    assert totals.total == 1440


# --- S1 -------------------------------------------------------------------------------------


def test_s1_single_short_day() -> None:
    result = plan(100, 200, 0, hm(6), PARAMS)

    assert result.status == PlanStatus.COMPLETE
    assert result.stop is None
    assert_timeline(
        result.segments,
        [
            (hm(6), hm(6, 15), Status.ON, Kind.PRETRIP),
            (hm(6, 15), hm(8, 15), Status.D, Kind.DRIVE),
            (hm(8, 15), hm(9, 15), Status.ON, Kind.PICKUP),
            (hm(9, 15), hm(13, 15), Status.D, Kind.DRIVE),
            (hm(13, 15), hm(14, 15), Status.ON, Kind.DROPOFF),
        ],
    )
    assert result.segments[-1].pos_end == 300.0
    assert result.route_miles == 300.0

    logs = build_daily_logs(result)
    assert len(logs) == 1
    assert_totals(logs[0].totals, off=15.75, sb=0, d=6, on=2.25)
    assert logs[0].miles == 300.0
    assert logs[0].recap.on_duty_today_min / 60 == 8.25
    assert logs[0].recap.cycle_used_min / 60 == 8.25
    assert logs[0].recap.available_min / 60 == 61.75
    assert logs[0].recap.last_5_days_min is None

    assert validate(result.segments, 0, PARAMS, result.departure, daily_logs=logs) == []


# --- S2 -------------------------------------------------------------------------------------


def test_s2_break_after_pickup_and_11h_limit_hit_exactly() -> None:
    result = plan(50, 500, 0, hm(5), PARAMS)

    assert result.status == PlanStatus.COMPLETE
    assert_timeline(
        result.segments,
        [
            (hm(5), hm(5, 15), Status.ON, Kind.PRETRIP),
            (hm(5, 15), hm(6, 15), Status.D, Kind.DRIVE),
            (hm(6, 15), hm(7, 15), Status.ON, Kind.PICKUP),
            (hm(7, 15), hm(15, 15), Status.D, Kind.DRIVE),
            (hm(15, 15), hm(15, 45), Status.OFF, Kind.BREAK),
            (hm(15, 45), hm(17, 45), Status.D, Kind.DRIVE),
            (hm(17, 45), hm(18, 45), Status.ON, Kind.DROPOFF),
        ],
    )
    assert result.route_miles == 550.0

    logs = build_daily_logs(result)
    assert len(logs) == 1
    assert_totals(logs[0].totals, off=10.75, sb=0, d=11, on=2.25)
    assert validate(result.segments, 0, PARAMS, result.departure, daily_logs=logs) == []


# --- S3 -------------------------------------------------------------------------------------


def test_s3_two_days_11h_limit_10h_rest_fuel_at_1000mi() -> None:
    result = plan(100, 1000, 0, hm(6), PARAMS)

    assert result.status == PlanStatus.COMPLETE
    assert_timeline(
        result.segments[:7],
        [
            (hm(6), hm(6, 15), Status.ON, Kind.PRETRIP),
            (hm(6, 15), hm(8, 15), Status.D, Kind.DRIVE),
            (hm(8, 15), hm(9, 15), Status.ON, Kind.PICKUP),
            (hm(9, 15), hm(17, 15), Status.D, Kind.DRIVE),
            (hm(17, 15), hm(17, 45), Status.OFF, Kind.BREAK),
            (hm(17, 45), hm(18, 45), Status.D, Kind.DRIVE),
            (hm(18, 45), hm(18, 45) + 600, Status.SB, Kind.REST),
        ],
    )
    # 10h rest crosses midnight: 18:45 day1 -> 04:45 day2 (600 min later)
    rest = result.segments[6]
    assert rest.start == hm(18, 45)
    assert rest.end == hm(18, 45) + 600 == 24 * 60 + hm(4, 45)

    assert_timeline(
        result.segments[7:],
        [
            (24 * 60 + hm(4, 45), 24 * 60 + hm(5), Status.ON, Kind.PRETRIP),
            (24 * 60 + hm(5), 24 * 60 + hm(13), Status.D, Kind.DRIVE),
            (24 * 60 + hm(13), 24 * 60 + hm(13, 30), Status.OFF, Kind.BREAK),
            (24 * 60 + hm(13, 30), 24 * 60 + hm(14, 30), Status.D, Kind.DRIVE),
            (24 * 60 + hm(14, 30), 24 * 60 + hm(15), Status.ON, Kind.FUEL),
            (24 * 60 + hm(15), 24 * 60 + hm(17), Status.D, Kind.DRIVE),
            (24 * 60 + hm(17), 24 * 60 + hm(18), Status.ON, Kind.DROPOFF),
        ],
    )
    assert result.route_miles == 1100.0
    assert result.segments[-1].pos_end == 1100.0

    logs = build_daily_logs(result)
    assert len(logs) == 2
    assert_totals(logs[0].totals, off=6.5, sb=5.25, d=11, on=1.25)
    assert logs[0].miles == 550.0
    assert_totals(logs[1].totals, off=6.5, sb=4.75, d=11, on=1.75)
    assert logs[1].miles == 550.0
    assert logs[1].recap.cycle_used_min / 60 == 25.0  # "Trip cycle used: 25 h"

    assert validate(result.segments, 0, PARAMS, result.departure, daily_logs=logs) == []


# --- S4 -------------------------------------------------------------------------------------


def test_s4_cycle_exhausted_mid_route_no_restart() -> None:
    result = plan(50, 800, hm(60), hm(6), PARAMS)  # cycle 60h = 3600 min

    assert result.status == PlanStatus.CYCLE_EXHAUSTED
    assert_timeline(
        result.segments,
        [
            (hm(6), hm(6, 15), Status.ON, Kind.PRETRIP),
            (hm(6, 15), hm(7, 15), Status.D, Kind.DRIVE),
            (hm(7, 15), hm(8, 15), Status.ON, Kind.PICKUP),
            (hm(8, 15), hm(16), Status.D, Kind.DRIVE),
        ],
    )
    stop = result.stop
    assert stop is not None
    assert stop.minute == hm(16)
    assert stop.mile == 437.5
    assert stop.blocked == Blocked.DRIVE
    assert stop.pending == (Kind.DROPOFF,)
    assert stop.unplanned_miles == 412.5
    assert stop.shortfall_min == 555
    assert result.route_miles == 850.0

    logs = build_daily_logs(result)
    assert len(logs) == 1
    assert_totals(logs[0].totals, off=14, sb=0, d=8.75, on=1.25)
    assert logs[0].recap.on_duty_today_min / 60 == 10
    assert logs[0].recap.cycle_used_min / 60 == 70
    assert logs[0].recap.available_min / 60 == 0
    assert not any(s.kind == Kind.RESTART for s in result.segments)  # no restart segment (D-2)

    assert validate(result.segments, hm(60), PARAMS, result.departure, daily_logs=logs) == []


# --- S4b ------------------------------------------------------------------------------------


def test_s4b_same_trip_with_the_internal_restart_option() -> None:
    result = plan(50, 800, hm(60), hm(6), PARAMS_RESTART)

    assert result.status == PlanStatus.COMPLETE
    assert result.stop is None

    # identical to S4 up to 16:00, then a 34 h restart instead of stopping
    prefix = result.segments[:4]
    assert_timeline(
        prefix,
        [
            (hm(6), hm(6, 15), Status.ON, Kind.PRETRIP),
            (hm(6, 15), hm(7, 15), Status.D, Kind.DRIVE),
            (hm(7, 15), hm(8, 15), Status.ON, Kind.PICKUP),
            (hm(8, 15), hm(16), Status.D, Kind.DRIVE),
        ],
    )
    restart = result.segments[4]
    assert restart.status == Status.OFF
    assert restart.kind == Kind.RESTART
    assert restart.start == hm(16)
    assert restart.end == hm(16) + 2040  # 34 h later: day 3, 02:00
    assert restart.end == 2 * 1440 + hm(2)

    rest_of_trip = result.segments[5:]
    day3 = 2 * 1440
    assert_timeline(
        rest_of_trip,
        [
            (day3 + hm(2), day3 + hm(2, 15), Status.ON, Kind.PRETRIP),
            (day3 + hm(2, 15), day3 + hm(10, 15), Status.D, Kind.DRIVE),
            (day3 + hm(10, 15), day3 + hm(10, 45), Status.OFF, Kind.BREAK),
            (day3 + hm(10, 45), day3 + hm(11), Status.D, Kind.DRIVE),
            (day3 + hm(11), day3 + hm(12), Status.ON, Kind.DROPOFF),
        ],
    )
    assert result.segments[-1].pos_end == 850.0
    assert result.route_miles == 850.0

    logs = build_daily_logs(result)
    assert len(logs) == 3
    assert_totals(logs[0].totals, off=14, sb=0, d=8.75, on=1.25)
    assert logs[0].recap.cycle_used_min / 60 == 70
    assert logs[0].recap.available_min / 60 == 0

    assert_totals(logs[1].totals, off=24, sb=0, d=0, on=0)
    assert logs[1].recap.cycle_used_min / 60 == 70  # restart has not completed yet
    assert logs[1].recap.available_min / 60 == 0

    assert_totals(logs[2].totals, off=14.5, sb=0, d=8.25, on=1.25)
    assert logs[2].recap.on_duty_today_min / 60 == 9.5
    assert logs[2].recap.cycle_used_min / 60 == 9.5
    assert logs[2].recap.available_min / 60 == 60.5

    assert (
        validate(result.segments, hm(60), PARAMS_RESTART, result.departure, daily_logs=logs) == []
    )
    # the restart is only legal because the option is on; the same segments must be rejected
    # by a validator call configured with the option off (D-2's "not reachable" guarantee)
    restart_violations = validate(result.segments, hm(60), PARAMS, result.departure)
    assert any(v.code.value == "V_RESTART_34" for v in restart_violations)


# --- S5 -------------------------------------------------------------------------------------


def test_s5a_almost_no_allowance_blocked_at_pretrip() -> None:
    result = plan(100, 200, 4194, hm(6), PARAMS)  # cycle 69.9 h, R = 6

    assert result.status == PlanStatus.CYCLE_EXHAUSTED
    assert result.segments == ()
    stop = result.stop
    assert stop is not None
    assert stop.minute == hm(6)
    assert stop.mile == 0.0
    assert stop.blocked == Blocked.PRETRIP
    assert stop.pending == (Kind.PICKUP, Kind.DROPOFF)
    assert stop.unplanned_miles == 300.0
    assert stop.shortfall_min == 474

    logs = build_daily_logs(result)
    assert len(logs) == 1
    assert_totals(logs[0].totals, off=24, sb=0, d=0, on=0)

    assert validate(result.segments, 4194, PARAMS, result.departure, daily_logs=logs) == []


def test_s5b_almost_no_allowance_a_sliver_of_driving() -> None:
    result = plan(100, 200, 4182, hm(6), PARAMS)  # cycle 69.7 h, R = 18

    assert result.status == PlanStatus.CYCLE_EXHAUSTED
    assert_timeline(
        result.segments,
        [
            (hm(6), hm(6, 15), Status.ON, Kind.PRETRIP),
            (hm(6, 15), hm(6, 18), Status.D, Kind.DRIVE),
        ],
    )
    assert result.segments[-1].pos_end == 2.5

    stop = result.stop
    assert stop is not None
    assert stop.mile == 2.5
    assert stop.blocked == Blocked.DRIVE
    assert stop.pending == (Kind.PICKUP, Kind.DROPOFF)
    assert stop.unplanned_miles == 297.5
    assert stop.shortfall_min == 477

    logs = build_daily_logs(result)
    assert_totals(logs[0].totals, off=23.7, sb=0, d=0.05, on=0.25)
    assert validate(result.segments, 4182, PARAMS, result.departure, daily_logs=logs) == []


# --- S6 -------------------------------------------------------------------------------------


def test_s6_the_dropoff_does_not_fit() -> None:
    result = plan(100, 200, hm(62), hm(6), PARAMS)  # cycle 62 h, R = 480

    assert result.status == PlanStatus.CYCLE_EXHAUSTED
    assert_timeline(
        result.segments,
        [
            (hm(6), hm(6, 15), Status.ON, Kind.PRETRIP),
            (hm(6, 15), hm(8, 15), Status.D, Kind.DRIVE),
            (hm(8, 15), hm(9, 15), Status.ON, Kind.PICKUP),
            (hm(9, 15), hm(13, 15), Status.D, Kind.DRIVE),
        ],
    )
    stop = result.stop
    assert stop is not None
    assert stop.minute == hm(13, 15)
    assert stop.mile == 300.0
    assert stop.blocked == Blocked.DROPOFF
    assert stop.pending == (Kind.DROPOFF,)
    assert stop.unplanned_miles == 0.0
    assert stop.shortfall_min == 15

    logs = build_daily_logs(result)
    assert_totals(logs[0].totals, off=16.75, sb=0, d=6, on=1.25)
    assert logs[0].recap.on_duty_today_min / 60 == 7.25
    assert logs[0].recap.cycle_used_min / 60 == 69.25
    assert logs[0].recap.available_min / 60 == 0.75

    assert validate(result.segments, hm(62), PARAMS, result.departure, daily_logs=logs) == []
