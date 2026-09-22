"""Every number in ``trips.hos.constants`` must equal the literal printed in hos-rules.md.

This is what keeps the document and the code from drifting apart silently (hos-rules.md section
10's closing note; implementation-plan.md section 4.1, "integer-minute guard").
"""

from trips.hos import constants as c


def test_limits_match_hos_rules_section_5() -> None:
    assert c.RESET_MIN == 600  # HOS-1: 10 hours
    assert c.DRIVE_LIMIT_MIN == 660  # HOS-2: 11 hours
    assert c.WINDOW_MIN == 840  # HOS-3: 14 hours
    assert c.BREAK_DRIVE_LIMIT_MIN == 480  # HOS-4: 8 cumulative driving hours
    assert c.BREAK_MIN == 30  # HOS-4: the interrupting run
    assert c.CYCLE_LIMIT_MIN == 4200  # HOS-5: 70 hours
    assert c.RESTART_MIN == 2040  # HOS-6: 34 hours
    assert c.CYCLE_DAYS == 8
    assert c.FUEL_INTERVAL_MILES == 1000  # FUEL-1


def test_assumption_defaults_match_hos_rules_section_3_2() -> None:
    assert c.PICKUP_MIN == 60  # A-1
    assert c.DROPOFF_MIN == 60  # A-2
    assert c.FUEL_STOP_MIN == 30  # A-4
    assert c.PRETRIP_MIN == 15  # A-6
    assert c.DEFAULT_AVG_SPEED_MPH == 55  # A-8 / D-5
    assert c.MAX_AVG_SPEED_MPH == 80


def test_every_limit_and_duration_is_an_int_minute() -> None:
    """Rule M-1 (D-4): every duration and limit inside trips.hos is an int number of minutes."""
    minute_valued = [
        c.RESET_MIN,
        c.DRIVE_LIMIT_MIN,
        c.WINDOW_MIN,
        c.BREAK_DRIVE_LIMIT_MIN,
        c.BREAK_MIN,
        c.CYCLE_LIMIT_MIN,
        c.RESTART_MIN,
        c.PICKUP_MIN,
        c.DROPOFF_MIN,
        c.FUEL_STOP_MIN,
        c.PRETRIP_MIN,
        c.CYCLE_DAYS,
        c.MINUTES_PER_HOUR,
        c.MINUTES_PER_DAY,
    ]
    assert all(type(v) is int for v in minute_valued)


def test_minutes_per_day_is_24_hours() -> None:
    assert c.MINUTES_PER_DAY == 1440
    assert c.MINUTES_PER_HOUR == 60
