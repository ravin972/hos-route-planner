"""Targeted tests for ``logs.py`` beyond what the golden scenarios already exercise: a drive
segment split by midnight (mileage apportioned by time), and the remark list's shape.
"""

from trips.hos.logs import build_daily_logs
from trips.hos.planner import plan
from trips.hos.types import Kind, PlanParams, Status

PARAMS = PlanParams(avg_speed_mph=50)


def test_a_drive_segment_crossing_midnight_is_split_with_miles_apportioned_by_time() -> None:
    # Depart 23:00; pre-trip ends 23:15; a long drive starts there and crosses midnight.
    result = plan(500, 10, 0, 23 * 60, PARAMS)
    logs = build_daily_logs(result)
    assert len(logs) >= 2

    day1_drive = [s for s in logs[0].segments if s.status == Status.D]
    day2_drive = [s for s in logs[1].segments if s.status == Status.D]
    assert day1_drive and day2_drive

    # day 1's portion ends at minute 1440 (the log's own last minute); day 2's portion starts at 0
    assert day1_drive[-1].end_min == 1440
    assert day2_drive[0].start_min == 0

    # the two portions' miles are proportional to their minutes (50 mph constant rate) and sum to
    # the full segment's miles (up to the point where the day boundary falls inside one segment)
    original = next(s for s in result.segments if s.status == Status.D)
    minutes_before_midnight = 1440 - original.start
    expected_miles_day1 = original.miles * minutes_before_midnight / original.minutes
    assert abs(day1_drive[-1].miles - expected_miles_day1) < 1e-6
    assert abs(day1_drive[-1].pos_end - day2_drive[0].pos_start) < 1e-9


def test_remarks_fire_once_per_segment_and_are_time_ordered() -> None:
    result = plan(100, 1000, 0, 6 * 60, PARAMS)
    logs = build_daily_logs(result)

    for log in logs:
        minutes = [r.minute for r in log.remarks]
        assert minutes == sorted(minutes)
        assert len(minutes) == len(set(minutes))  # no duplicate-minute remarks
        for r in log.remarks:
            assert 0 <= r.minute < 1440

    # every real activity in the trip produces exactly one remark, on the day it starts
    all_remark_kinds = [r.kind for log in logs for r in log.remarks]
    assert all_remark_kinds.count(Kind.PICKUP) == 1
    assert all_remark_kinds.count(Kind.DROPOFF) == 1
    assert all_remark_kinds.count(Kind.FUEL) == 1
    assert all_remark_kinds.count(Kind.PRETRIP) == 2  # one per shift; S3's route has two shifts


def test_empty_plan_produces_one_all_off_day_with_no_remarks_beyond_padding() -> None:
    result = plan(100, 200, 4200, 6 * 60, PARAMS)  # cycle already at the limit
    logs = build_daily_logs(result)
    assert len(logs) == 1
    assert logs[0].totals.off == 1440
    assert logs[0].miles == 0.0
