"""The 11 property-based invariants in hos-rules.md section 11 ("Property-based invariants").

architecture.md and implementation-plan.md name Hypothesis as the property-testing library for
Phase 1, but it is not installed, and the Phase 1 instructions for this session say not to install
new dependencies. This is a tooling substitution, not a rule change: every one of the 11 invariants
below is still implemented and checked, using Python's stdlib ``random`` with a fixed seed per
property (so a failure is reproducible -- the seed and the generated scenario are printed via the
assertion message) instead of Hypothesis's generation and shrinking. Flagged in the G2 report.
"""

import random

from trips.hos.logs import build_daily_logs
from trips.hos.planner import plan
from trips.hos.types import Kind, PlanParams, PlanStatus, Status
from trips.hos.validator import validate

MIN_MPH, MAX_MPH = 45, 65
MAX_LEG_MILES = 3000
MAX_CYCLE_MIN = 4200
MAX_DEPARTURE_DAY = 10


def scenarios(seed: int, n: int):
    """``n`` random (leg1_miles, leg2_miles, cycle_used_min, mph, departure) tuples."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        leg1 = round(rng.uniform(0, MAX_LEG_MILES), 2)
        leg2 = round(rng.uniform(0, MAX_LEG_MILES), 2)
        cycle = rng.randint(0, MAX_CYCLE_MIN)
        mph = rng.randint(MIN_MPH, MAX_MPH)
        departure = rng.randint(0, MAX_DEPARTURE_DAY * 1440)
        out.append((leg1, leg2, cycle, mph, departure))
    return out


def _plan(leg1, leg2, cycle, mph, departure, allow_restart=False):
    params = PlanParams(avg_speed_mph=mph, allow_34_hour_restart=allow_restart)
    return plan(leg1, leg2, cycle, departure, params), params


def _describe(leg1, leg2, cycle, mph, departure) -> str:
    return f"leg1={leg1} leg2={leg2} cycle_min={cycle} mph={mph} departure={departure}"


# --- property 1: every produced plan validates clean --------------------------------------------


def test_property_1_every_plan_validates_clean() -> None:
    for leg1, leg2, cycle, mph, departure in scenarios(seed=1, n=200):
        result, params = _plan(leg1, leg2, cycle, mph, departure)
        violations = validate(result.segments, cycle, params, departure)
        assert violations == [], f"{_describe(leg1, leg2, cycle, mph, departure)}: {violations}"


def test_property_1b_restart_option_plans_also_validate_clean() -> None:
    for leg1, leg2, cycle, mph, departure in scenarios(seed=101, n=100):
        result, params = _plan(leg1, leg2, cycle, mph, departure, allow_restart=True)
        violations = validate(result.segments, cycle, params, departure)
        assert violations == [], f"{_describe(leg1, leg2, cycle, mph, departure)}: {violations}"


# --- property 2: contiguous, sorted, integer-minute; starts at departure ------------------------


def test_property_2_segments_are_contiguous_sorted_integer_and_start_at_departure() -> None:
    for leg1, leg2, cycle, mph, departure in scenarios(seed=2, n=200):
        result, _ = _plan(leg1, leg2, cycle, mph, departure)
        segs = result.segments
        desc = _describe(leg1, leg2, cycle, mph, departure)
        if segs:
            assert segs[0].start == departure, desc
        for a, b in zip(segs, segs[1:], strict=False):
            assert a.end == b.start, desc
            assert a.start < a.end, desc
        for s in segs:
            assert type(s.start) is int and type(s.end) is int, desc


# --- property 3: driven miles equal (or fall short of) the route ---------------------------------


def test_property_3_driven_miles_match_the_route() -> None:
    for leg1, leg2, cycle, mph, departure in scenarios(seed=3, n=200):
        result, _ = _plan(leg1, leg2, cycle, mph, departure)
        driven = sum(s.miles for s in result.segments if s.status == Status.D)
        desc = _describe(leg1, leg2, cycle, mph, departure)
        if result.status == PlanStatus.COMPLETE:
            assert abs(driven - result.route_miles) < 0.01, desc
        else:
            assert driven <= result.route_miles + 0.01, desc


# --- property 4: every daily log sums to 1,440 min; row totals equal the drawn segments ----------


def test_property_4_daily_logs_sum_to_1440_and_totals_match_segments() -> None:
    for leg1, leg2, cycle, mph, departure in scenarios(seed=4, n=150):
        result, _ = _plan(leg1, leg2, cycle, mph, departure)
        desc = _describe(leg1, leg2, cycle, mph, departure)
        for log in build_daily_logs(result):
            assert log.totals.total == 1440, desc
            assert sum(s.minutes for s in log.segments) == 1440, desc
            assert (
                sum(s.minutes for s in log.segments if s.status == Status.OFF) == log.totals.off
            ), desc
            assert sum(s.minutes for s in log.segments if s.status == Status.SB) == log.totals.sb, (
                desc
            )
            assert sum(s.minutes for s in log.segments if s.status == Status.D) == log.totals.d, (
                desc
            )
            assert sum(s.minutes for s in log.segments if s.status == Status.ON) == log.totals.on, (
                desc
            )


# --- property 5: stop mileage non-decreasing; >= 1 fuel stop per 1,000 planned miles --------------


def test_property_5_mileage_is_non_decreasing_and_fuel_covers_the_distance() -> None:
    for leg1, leg2, cycle, mph, departure in scenarios(seed=5, n=200):
        result, _ = _plan(leg1, leg2, cycle, mph, departure)
        desc = _describe(leg1, leg2, cycle, mph, departure)
        last = 0.0
        for s in result.segments:
            assert s.pos_start >= last - 1e-9, desc
            assert s.pos_end >= s.pos_start - 1e-9, desc
            last = s.pos_end

        driven = sum(s.miles for s in result.segments if s.status == Status.D)
        fuel_stops = sum(1 for s in result.segments if s.kind == Kind.FUEL)
        # at least one fuel stop for every full 1,000 mi actually driven (a partial last segment
        # under 1,000 mi needs none)
        assert fuel_stops >= int(driven // 1000), desc


# --- property 6: deterministic ------------------------------------------------------------------


def test_property_6_same_input_gives_byte_identical_output() -> None:
    for leg1, leg2, cycle, mph, departure in scenarios(seed=6, n=100):
        params = PlanParams(avg_speed_mph=mph)
        a = plan(leg1, leg2, cycle, departure, params)
        b = plan(leg1, leg2, cycle, departure, params)
        assert a == b, _describe(leg1, leg2, cycle, mph, departure)


# --- property 7: metamorphic -- shifting departure by +24h shifts every timestamp by +24h --------


def test_property_7_shifting_departure_by_24h_shifts_every_timestamp() -> None:
    for leg1, leg2, cycle, mph, departure in scenarios(seed=7, n=100):
        params = PlanParams(avg_speed_mph=mph)
        a = plan(leg1, leg2, cycle, departure, params)
        b = plan(leg1, leg2, cycle, departure + 1440, params)
        desc = _describe(leg1, leg2, cycle, mph, departure)

        assert len(a.segments) == len(b.segments), desc
        for sa, sb in zip(a.segments, b.segments, strict=True):
            assert sb.start == sa.start + 1440, desc
            assert sb.end == sa.end + 1440, desc
            assert sb.status == sa.status, desc
            assert sb.kind == sa.kind, desc
            assert sb.pos_start == sa.pos_start, desc
            assert sb.pos_end == sa.pos_end, desc
        assert a.status == b.status, desc
        if a.stop is not None:
            assert b.stop is not None, desc
            assert b.stop.minute == a.stop.minute + 1440, desc
            assert b.stop.mile == a.stop.mile, desc
            assert b.stop.blocked == a.stop.blocked, desc
            assert b.stop.shortfall_min == a.stop.shortfall_min, desc


# --- property 8: cycle cap -----------------------------------------------------------------------


def test_property_8_scheduled_on_duty_minutes_never_exceed_the_remaining_allowance() -> None:
    for leg1, leg2, cycle, mph, departure in scenarios(seed=8, n=200):
        result, _ = _plan(leg1, leg2, cycle, mph, departure)
        on_duty = sum(s.minutes for s in result.segments if s.status in (Status.D, Status.ON))
        assert on_duty <= 4200 - cycle, _describe(leg1, leg2, cycle, mph, departure)


# --- property 9: status consistency ---------------------------------------------------------------


def test_property_9_status_consistency() -> None:
    for leg1, leg2, cycle, mph, departure in scenarios(seed=9, n=200):
        result, _ = _plan(leg1, leg2, cycle, mph, departure)
        desc = _describe(leg1, leg2, cycle, mph, departure)
        dropoff_done = any(s.kind == Kind.DROPOFF for s in result.segments)

        if result.status == PlanStatus.COMPLETE:
            assert dropoff_done, desc
            assert result.stop is None, desc
        else:
            assert not dropoff_done, desc
            assert result.stop is not None, desc
            assert result.stop.shortfall_min >= 1, desc

        assert not any(s.kind == Kind.RESTART for s in result.segments), desc  # option is off


def test_property_9b_status_consistency_with_restart_allowed() -> None:
    """With the option on, every plan is complete (a wall is always eventually resolved by a
    restart, since a fresh 4,200-min cycle always covers at least one more shift's worth of
    progress), and the drop-off is always performed."""
    for leg1, leg2, cycle, mph, departure in scenarios(seed=109, n=100):
        result, _ = _plan(leg1, leg2, cycle, mph, departure, allow_restart=True)
        desc = _describe(leg1, leg2, cycle, mph, departure)
        assert result.status == PlanStatus.COMPLETE, desc
        assert result.stop is None, desc
        assert any(s.kind == Kind.DROPOFF for s in result.segments), desc


# --- property 10: prefix property ----------------------------------------------------------------


def test_property_10_more_cycle_used_never_produces_a_longer_plan() -> None:
    """For cycle_b >= cycle_a (same route, speed, departure), plan b never drives, or otherwise
    accomplishes, more than plan a -- and is never complete when a is not."""
    rng = random.Random(10)
    for _ in range(150):
        leg1 = round(rng.uniform(0, MAX_LEG_MILES), 2)
        leg2 = round(rng.uniform(0, MAX_LEG_MILES), 2)
        mph = rng.randint(MIN_MPH, MAX_MPH)
        departure = rng.randint(0, MAX_DEPARTURE_DAY * 1440)
        cycle_a = rng.randint(0, MAX_CYCLE_MIN)
        cycle_b = rng.randint(cycle_a, MAX_CYCLE_MIN)
        params = PlanParams(avg_speed_mph=mph)

        a = plan(leg1, leg2, cycle_a, departure, params)
        b = plan(leg1, leg2, cycle_b, departure, params)
        desc = f"leg1={leg1} leg2={leg2} mph={mph} departure={departure} a={cycle_a} b={cycle_b}"

        driven_a = sum(s.miles for s in a.segments if s.status == Status.D)
        driven_b = sum(s.miles for s in b.segments if s.status == Status.D)
        assert driven_b <= driven_a + 0.01, desc
        if a.status != PlanStatus.COMPLETE:
            assert b.status != PlanStatus.COMPLETE, desc


# --- property 11: no redundant break --------------------------------------------------------------


def test_property_11_every_break_starts_exactly_when_due() -> None:
    """Every planner-scheduled ``break`` segment starts with exactly 480 min of driving
    accumulated since the last qualifying (>= 30 min) non-driving run -- never earlier, and it is
    never scheduled again before it is due (decision D-3)."""
    for leg1, leg2, cycle, mph, departure in scenarios(seed=11, n=150):
        result, _ = _plan(leg1, leg2, cycle, mph, departure)
        desc = _describe(leg1, leg2, cycle, mph, departure)

        drive_since_break = 0
        nondrive_run = 0
        for s in result.segments:
            if s.status == Status.D:
                if s.kind == Kind.DRIVE:
                    drive_since_break += s.minutes
                nondrive_run = 0
            else:
                if s.kind == Kind.BREAK:
                    assert drive_since_break == 480, (
                        f"{desc}: break started with {drive_since_break} min driven, not 480"
                    )
                nondrive_run += s.minutes
                if nondrive_run >= 30:
                    drive_since_break = 0
