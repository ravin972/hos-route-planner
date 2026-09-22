"""Direct tests of ``validator.py``: the structural checks, every rule-content boundary in
hos-rules.md section 11's "30-minute interruption" and "Reset and limits" groups (built as
hand-crafted segment lists, independent of the planner), and the mutation self-test required by
implementation-plan.md section 4.1: take a valid plan, mutate it by one minute, and expect the
exact violation code -- one mutation per one of the twelve codes.
"""

import dataclasses

from trips.hos.logs import build_daily_logs
from trips.hos.planner import plan
from trips.hos.types import Kind, PlanParams, Segment, Status
from trips.hos.validator import validate

PARAMS = PlanParams(avg_speed_mph=50)
DEPARTURE = 6 * 60


def chain(
    departure: int, steps: list[tuple[Status, Kind, int]], start_pos: float = 0.0
) -> list[Segment]:
    """Build a contiguous segment list from (status, kind, minutes) steps; no segment drives."""
    segs = []
    t = departure
    for status, kind, minutes in steps:
        segs.append(Segment(t, t + minutes, status, kind, start_pos, start_pos, ""))
        t += minutes
    return segs


def codes(violations) -> set[str]:
    return {v.code.value for v in violations}


# --- structural checks -------------------------------------------------------------------------


def test_valid_minimal_timeline_has_no_violations() -> None:
    segs = chain(DEPARTURE, [(Status.ON, Kind.PRETRIP, 15), (Status.OFF, Kind.IDLE, 30)])
    assert validate(segs, 0, PARAMS, DEPARTURE) == []


def test_empty_segments_with_matching_departure_is_valid() -> None:
    assert validate([], 0, PARAMS, DEPARTURE) == []


def test_wrong_status_type_is_flagged() -> None:
    segs = chain(DEPARTURE, [(Status.ON, Kind.PRETRIP, 15)])
    bad = [dataclasses.replace(segs[0], status="NOPE")]  # type: ignore[arg-type]
    assert "V_STATUS" in codes(validate(bad, 0, PARAMS, DEPARTURE))


def test_wrong_kind_type_is_flagged() -> None:
    segs = chain(DEPARTURE, [(Status.ON, Kind.PRETRIP, 15)])
    bad = [dataclasses.replace(segs[0], kind="nope")]  # type: ignore[arg-type]
    assert "V_STATUS" in codes(validate(bad, 0, PARAMS, DEPARTURE))


def test_non_int_boundary_is_flagged() -> None:
    segs = chain(DEPARTURE, [(Status.ON, Kind.PRETRIP, 15)])
    bad = [dataclasses.replace(segs[0], end=segs[0].end + 0.5)]  # type: ignore[arg-type]
    assert "V_INTEGER" in codes(validate(bad, 0, PARAMS, DEPARTURE))


def test_non_positive_duration_is_flagged() -> None:
    bad = [Segment(DEPARTURE, DEPARTURE, Status.ON, Kind.PRETRIP, 0.0, 0.0)]
    assert "V_STATUS" in codes(validate(bad, 0, PARAMS, DEPARTURE))


def test_timeline_not_starting_at_departure_is_flagged() -> None:
    segs = chain(DEPARTURE + 5, [(Status.ON, Kind.PRETRIP, 15)])
    assert "V_GAP" in codes(validate(segs, 0, PARAMS, DEPARTURE))


def test_a_gap_between_segments_is_flagged() -> None:
    segs = chain(DEPARTURE, [(Status.ON, Kind.PRETRIP, 15), (Status.D, Kind.DRIVE, 60)])
    segs[1] = dataclasses.replace(segs[1], start=segs[1].start + 1, end=segs[1].end + 1)
    assert "V_GAP" in codes(validate(segs, 0, PARAMS, DEPARTURE))


def test_an_overlap_between_segments_is_flagged() -> None:
    segs = chain(DEPARTURE, [(Status.ON, Kind.PRETRIP, 15), (Status.D, Kind.DRIVE, 60)])
    segs[0] = dataclasses.replace(segs[0], end=segs[0].end + 1)
    assert "V_OVERLAP" in codes(validate(segs, 0, PARAMS, DEPARTURE))


# --- HOS-4, the 30-minute interruption: combination rules --------------------------------------


def test_two_separate_15_min_stops_do_not_satisfy_hos4() -> None:
    """Two 15-min non-driving runs separated by driving never combine (hos-rules.md HOS-4)."""
    segs = chain(
        DEPARTURE,
        [
            (Status.ON, Kind.PRETRIP, 15),
            (Status.D, Kind.DRIVE, 480),  # drive_since_break -> 480 exactly
            (Status.OFF, Kind.IDLE, 15),  # first 15-min stop: insufficient alone
            (Status.D, Kind.DRIVE, 30),  # second stop pending; this D minute should violate
            (Status.OFF, Kind.IDLE, 15),  # second 15-min stop
            (Status.D, Kind.DRIVE, 1),
        ],
    )
    violations = validate(segs, 0, PARAMS, DEPARTURE)
    assert "V_BREAK_30" in codes(violations)


def test_15_min_on_plus_15_min_off_adjacent_do_satisfy_hos4() -> None:
    """guide p.10's own example: 15 min on-duty-not-driving + 15 min off-duty, consecutive,
    satisfies the 30-minute interruption -- no violation, and no redundant break either."""
    segs = chain(
        DEPARTURE,
        [
            (Status.ON, Kind.PRETRIP, 15),
            (Status.D, Kind.DRIVE, 480),
            (Status.ON, Kind.FUEL, 15),  # generic on-duty stop, not full-length
            (Status.OFF, Kind.IDLE, 15),  # immediately adjacent -> 30 min combined
            (Status.D, Kind.DRIVE, 60),
        ],
    )
    assert validate(segs, 0, PARAMS, DEPARTURE) == []


def test_a_29_minute_off_does_not_reset_the_break_clock() -> None:
    segs = chain(
        DEPARTURE,
        [
            (Status.ON, Kind.PRETRIP, 15),
            (Status.D, Kind.DRIVE, 480),
            (Status.OFF, Kind.IDLE, 29),
            (Status.D, Kind.DRIVE, 1),
        ],
    )
    assert "V_BREAK_30" in codes(validate(segs, 0, PARAMS, DEPARTURE))


def test_pickup_fuel_and_dropoff_each_reset_the_break_clock_with_no_redundant_break() -> None:
    """A 60-min pickup, a 30-min fuel stop and a 60-min drop-off each independently satisfy
    HOS-4 on their own -- decision D-3, property 11."""
    for kind, minutes in ((Kind.PICKUP, 60), (Kind.FUEL, 30), (Kind.DROPOFF, 60)):
        segs = chain(
            DEPARTURE,
            [
                (Status.ON, Kind.PRETRIP, 15),
                (Status.D, Kind.DRIVE, 480),
                (Status.ON, kind, minutes),
                (Status.D, Kind.DRIVE, 60),
            ],
        )
        assert validate(segs, 0, PARAMS, DEPARTURE) == [], f"{kind} of {minutes} min should reset"


def test_exactly_480_min_driven_then_arrival_needs_no_break() -> None:
    """Driving stops exactly at the 480-minute mark (no further D minute starts) -- legal."""
    segs = chain(
        DEPARTURE,
        [(Status.ON, Kind.PRETRIP, 15), (Status.D, Kind.DRIVE, 480), (Status.ON, Kind.DROPOFF, 60)],
    )
    assert validate(segs, 0, PARAMS, DEPARTURE) == []


# --- HOS-1 / HOS-6: the reset and restart runs --------------------------------------------------


def test_9h59m_sb_does_not_reset() -> None:
    segs = chain(
        DEPARTURE,
        [
            (Status.ON, Kind.PRETRIP, 15),
            (Status.D, Kind.DRIVE, 660),  # exactly the 11 h limit
            (Status.SB, Kind.REST, 599),  # one minute short of a real reset
            (Status.ON, Kind.PRETRIP, 15),
            (Status.D, Kind.DRIVE, 1),
        ],
    )
    violations = validate(segs, 0, PARAMS, DEPARTURE)
    assert "V_DRIVE_11" in codes(violations)


def test_sb_interrupted_by_on_does_not_reset() -> None:
    segs = chain(
        DEPARTURE,
        [
            (Status.ON, Kind.PRETRIP, 15),
            (Status.D, Kind.DRIVE, 660),
            (Status.SB, Kind.IDLE, 300),
            (Status.ON, Kind.FUEL, 5),  # breaks the OFF/SB-only run (HOS-1's own wording)
            (Status.SB, Kind.IDLE, 300),  # only 300 more, and the run restarted at 0
            (Status.ON, Kind.PRETRIP, 15),
            (Status.D, Kind.DRIVE, 1),
        ],
    )
    violations = validate(segs, 0, PARAMS, DEPARTURE)
    assert "V_DRIVE_11" in codes(violations)


def test_exactly_660_min_driven_is_legal() -> None:
    """660 min total driving, split by the mandatory 30-min break at the 480-min mark so HOS-4
    is satisfied too -- isolates the HOS-2 boundary (druv_shift == 660 is legal, not over)."""
    segs = chain(
        DEPARTURE,
        [
            (Status.ON, Kind.PRETRIP, 15),
            (Status.D, Kind.DRIVE, 480),
            (Status.OFF, Kind.BREAK, 30),
            (Status.D, Kind.DRIVE, 180),
            (Status.ON, Kind.DROPOFF, 60),
        ],
    )
    assert validate(segs, 0, PARAMS, DEPARTURE) == []


def test_a_real_2040_min_off_sb_run_resets_the_cycle() -> None:
    """A genuine 2,040-min OFF/SB run resets the cycle to 0, so starting fully exhausted
    (carry-in = 4,200) is legal again immediately after it, before any of it 'ages' back off."""
    segs = chain(
        DEPARTURE,
        [
            (Status.OFF, Kind.RESTART, 2040),
            (Status.ON, Kind.PRETRIP, 15),
            (Status.D, Kind.DRIVE, 480),
            (Status.OFF, Kind.BREAK, 30),
            (Status.D, Kind.DRIVE, 180),
        ],
    )
    params_restart = PlanParams(avg_speed_mph=50, allow_34_hour_restart=True)
    assert validate(segs, 4200, params_restart, DEPARTURE) == []  # even starting fully exhausted


# --- FUEL-1 --------------------------------------------------------------------------------------


def test_exactly_1000_miles_between_fuelings_is_legal() -> None:
    result = plan(100, 1000, 0, DEPARTURE, PARAMS)  # S3's own route touches exactly 1,000 mi
    assert validate(result.segments, 0, PARAMS, DEPARTURE) == []


def test_over_1000_miles_between_fuelings_is_flagged() -> None:
    segs = [
        Segment(DEPARTURE, DEPARTURE + 15, Status.ON, Kind.PRETRIP, 0.0, 0.0),
        Segment(DEPARTURE + 15, DEPARTURE + 15 + 1300, Status.D, Kind.DRIVE, 0.0, 1083.3),
    ]
    assert "V_FUEL_1000" in codes(validate(segs, 0, PARAMS, DEPARTURE))


# --- V_DAY_1440 ------------------------------------------------------------------------------


def test_v_day_1440_passes_for_every_golden_scenario_log() -> None:
    from trips.hos.validator import validate_daily_logs

    for leg1, leg2, cycle in ((100, 200, 0), (50, 500, 0), (100, 1000, 0)):
        result = plan(leg1, leg2, cycle, DEPARTURE, PARAMS)
        logs = build_daily_logs(result)
        assert validate_daily_logs(logs) == []


def test_v_day_1440_flags_a_short_day() -> None:
    from trips.hos.types import DailyLog, DutyTotals, LogSegment, Recap
    from trips.hos.validator import validate_daily_logs

    short_log = DailyLog(
        day_index=0,
        day_number=1,
        segments=(LogSegment(0, 1439, Status.OFF, Kind.IDLE, 0.0, 0.0),),  # 1 min short
        totals=DutyTotals(off=1439, sb=0, d=0, on=0),
        miles=0.0,
        remarks=(),
        recap=Recap(0, 0, 4200),
    )
    violations = validate_daily_logs([short_log])
    assert "V_DAY_1440" in codes(violations)


# --- the mutation self-test: one mutation per violation code ------------------------------------


def _valid_plan() -> tuple[Segment, ...]:
    return plan(100, 1000, 0, DEPARTURE, PARAMS).segments  # touches fuel, rest, break, 2 days


def _shift_tail(segs: list[Segment], from_index: int, delta: int) -> list[Segment]:
    """Shift every segment from ``from_index`` onward by ``delta`` minutes, keeping the timeline
    contiguous, so a duration mutation does not also trip the structural gap/overlap checks."""
    out = list(segs[:from_index])
    for seg in segs[from_index:]:
        out.append(dataclasses.replace(seg, start=seg.start + delta, end=seg.end + delta))
    return out


def test_mutation_extend_a_drive_segment_past_11h_triggers_v_drive_11() -> None:
    segs = list(_valid_plan())
    drive_idx = next(i for i, s in enumerate(segs) if s.kind == Kind.DRIVE and s.minutes >= 480)
    segs[drive_idx] = dataclasses.replace(segs[drive_idx], end=segs[drive_idx].end + 1)
    mutated = _shift_tail(segs, drive_idx + 1, 1)
    assert "V_DRIVE_11" in codes(validate(mutated, 0, PARAMS, DEPARTURE))


def test_mutation_shrink_the_rest_below_600_triggers_v_reset_10() -> None:
    segs = list(_valid_plan())
    rest_idx = next(i for i, s in enumerate(segs) if s.kind == Kind.REST)
    segs[rest_idx] = dataclasses.replace(segs[rest_idx], end=segs[rest_idx].end - 1)
    mutated = _shift_tail(segs, rest_idx + 1, -1)
    assert "V_RESET_10" in codes(validate(mutated, 0, PARAMS, DEPARTURE))


def test_mutation_shrink_a_qualifying_break_below_30_triggers_v_break_30() -> None:
    segs = list(_valid_plan())
    break_idx = next(i for i, s in enumerate(segs) if s.kind == Kind.BREAK)
    segs[break_idx] = dataclasses.replace(segs[break_idx], end=segs[break_idx].end - 1)
    mutated = _shift_tail(segs, break_idx + 1, -1)
    assert "V_BREAK_30" in codes(validate(mutated, 0, PARAMS, DEPARTURE))


def test_mutation_remove_the_fuel_stop_triggers_v_fuel_1000() -> None:
    segs = list(_valid_plan())
    fuel_idx = next(i for i, s in enumerate(segs) if s.kind == Kind.FUEL)
    fuel_len = segs[fuel_idx].minutes
    del segs[fuel_idx]
    mutated = _shift_tail(segs, fuel_idx, -fuel_len)
    assert "V_FUEL_1000" in codes(validate(mutated, 0, PARAMS, DEPARTURE))


def test_mutation_push_the_window_past_14h_triggers_v_window_14() -> None:
    """Widen the break before the first shift's last drive segment enough that the drive's start
    crosses the 14 h window close (departure + 840 min), without disturbing the drive or cycle
    clocks (a longer OFF break does not add driving, and the break itself already qualifies
    HOS-4 at 30 min, so widening it past 30 changes nothing else)."""
    segs = list(_valid_plan())
    last_drive_of_shift1 = max(
        i for i, s in enumerate(segs[:7]) if s.kind == Kind.DRIVE
    )  # the pre-rest drive segments are segs[0:7] per S3's shape
    window_close = DEPARTURE + 840
    delay = window_close - segs[last_drive_of_shift1].start + 1  # push the start 1 min past close

    segs[last_drive_of_shift1] = dataclasses.replace(
        segs[last_drive_of_shift1],
        start=segs[last_drive_of_shift1].start + delay,
        end=segs[last_drive_of_shift1].end + delay,
    )
    segs[last_drive_of_shift1 - 1] = dataclasses.replace(
        segs[last_drive_of_shift1 - 1], end=segs[last_drive_of_shift1 - 1].end + delay
    )
    mutated = _shift_tail(segs, last_drive_of_shift1 + 1, delay)
    violations = validate(mutated, 0, PARAMS, DEPARTURE)
    assert "V_WINDOW_14" in codes(violations)


def test_mutation_restart_segment_without_the_option_triggers_v_restart_34() -> None:
    restart_plan = plan(
        50, 800, 60 * 60, DEPARTURE, PlanParams(avg_speed_mph=50, allow_34_hour_restart=True)
    )
    violations = validate(restart_plan.segments, 60 * 60, PARAMS, DEPARTURE)  # option off here
    assert "V_RESTART_34" in codes(violations)


def test_mutation_shrink_a_restart_segment_below_2040_triggers_v_restart_34() -> None:
    restart_plan = plan(
        50, 800, 60 * 60, DEPARTURE, PlanParams(avg_speed_mph=50, allow_34_hour_restart=True)
    )
    segs = list(restart_plan.segments)
    restart_idx = next(i for i, s in enumerate(segs) if s.kind == Kind.RESTART)
    segs[restart_idx] = dataclasses.replace(segs[restart_idx], end=segs[restart_idx].end - 1)
    mutated = _shift_tail(segs, restart_idx + 1, -1)
    params_restart = PlanParams(avg_speed_mph=50, allow_34_hour_restart=True)
    assert "V_RESTART_34" in codes(validate(mutated, 60 * 60, params_restart, DEPARTURE))


def test_mutation_overconsume_the_cycle_triggers_v_cycle_70() -> None:
    """Start 1 minute short of the full trip's on-duty consumption: the plan produced still
    schedules the same on-duty minutes (validate does not re-plan), so replayed against a
    carry-in that leaves only 1 min of true headroom, the total must exceed 4,200."""
    segs = _valid_plan()
    on_duty_total = sum(s.minutes for s in segs if s.status in (Status.D, Status.ON))
    carry_in = 4200 - on_duty_total + 1  # 1 minute over the limit by the end
    assert "V_CYCLE_70" in codes(validate(segs, carry_in, PARAMS, DEPARTURE))


def test_mutation_bad_status_triggers_v_status() -> None:
    segs = list(_valid_plan())
    segs[0] = dataclasses.replace(segs[0], status="XX")  # type: ignore[arg-type]
    assert "V_STATUS" in codes(validate(segs, 0, PARAMS, DEPARTURE))


def test_mutation_float_boundary_triggers_v_integer() -> None:
    segs = list(_valid_plan())
    segs[0] = dataclasses.replace(segs[0], end=segs[0].end + 0.5)  # type: ignore[arg-type]
    assert "V_INTEGER" in codes(validate(segs, 0, PARAMS, DEPARTURE))


def test_mutation_introduce_a_gap_triggers_v_gap() -> None:
    segs = list(_valid_plan())
    mutated = _shift_tail(segs, 1, 1)
    assert "V_GAP" in codes(validate(mutated, 0, PARAMS, DEPARTURE))


def test_mutation_introduce_an_overlap_triggers_v_overlap() -> None:
    segs = list(_valid_plan())
    segs[0] = dataclasses.replace(segs[0], end=segs[0].end + 1)
    assert "V_OVERLAP" in codes(validate(segs, 0, PARAMS, DEPARTURE))
