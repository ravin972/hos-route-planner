"""The event-driven planner (hos-rules.md section 8, decisions D-1 through D-5).

Deterministic, greedy: do as much as legally possible, and rest, fuel or break only when a limit
actually binds. ``plan()`` is a pure function of its arguments -- no clock, no I/O, no randomness;
"now" is resolved by the caller via ``departure``.

Positions are tracked as ``fractions.Fraction`` internally so that ``ceil``/``floor`` mile-to-minute
conversions are exact regardless of how many stops a route needs -- floats appear only at the two
boundaries the rules require: they are the type of ``avg_speed_mph`` coming in, and of every
``Segment.pos_*`` going out (rule M-1, decision D-4: minutes are the only thing that must never be
a float; miles may be).
"""

import math
from fractions import Fraction

from . import constants as c
from .types import Blocked, CycleStop, Kind, PlanParams, PlanResult, PlanStatus, Segment, Status

_MILESTONE_NOTE: dict[Kind, str] = {Kind.PICKUP: "Pickup", Kind.DROPOFF: "Drop-off"}
_MILESTONE_BLOCKED: dict[Kind, Blocked] = {
    Kind.PICKUP: Blocked.PICKUP,
    Kind.DROPOFF: Blocked.DROPOFF,
}


def _exact(value: float) -> Fraction:
    """The precise ``Fraction`` for a float's actual binary value -- no decimal reinterpretation,
    just no further rounding error from here on."""
    return Fraction(*float(value).as_integer_ratio())


def plan(
    leg1_miles: float,
    leg2_miles: float,
    cycle_used_min: int,
    departure: int,
    params: PlanParams,
) -> PlanResult:
    """Plan a trip: current -> pickup (``leg1_miles``) -> drop-off (``leg2_miles``).

    ``departure`` and every ``Segment`` boundary are absolute minutes since a shared, arbitrary
    epoch whose day 0 starts at local midnight (so ``minute // 1440`` is the calendar day, and
    shifting ``departure`` by 1,440 shifts every output timestamp by exactly that much -- property
    7 in hos-rules.md section 11). ``cycle_used_min`` is the starting consumed cycle (A-13).
    """
    if type(cycle_used_min) is not int or not (0 <= cycle_used_min <= c.CYCLE_LIMIT_MIN):
        raise ValueError(
            f"cycle_used_min must be an int in [0, {c.CYCLE_LIMIT_MIN}], got {cycle_used_min!r}"
        )
    if type(departure) is not int:
        raise TypeError(f"departure must be an int minute, got {type(departure).__name__}")
    for name, miles in (("leg1_miles", leg1_miles), ("leg2_miles", leg2_miles)):
        if isinstance(miles, bool) or not isinstance(miles, int | float):
            raise TypeError(f"{name} must be a number, not {type(miles).__name__}")
        if not math.isfinite(miles) or miles < 0:
            raise ValueError(f"{name} must be a finite number >= 0, got {miles}")
    if not isinstance(params, PlanParams):
        raise TypeError(f"params must be a PlanParams, got {type(params).__name__}")

    speed = _exact(params.avg_speed_mph)
    fuel_interval = _exact(params.fuel_interval_miles)
    leg1 = _exact(leg1_miles)
    route_miles = leg1 + _exact(leg2_miles)
    milestones: list[tuple[Kind, Fraction, int]] = [
        (Kind.PICKUP, leg1, params.pickup_min),
        (Kind.DROPOFF, route_miles, params.dropoff_min),
    ]

    t = departure
    cycle = cycle_used_min
    pos = Fraction(0)
    drive_shift = 0
    drive_since_break = 0
    window_open: int | None = None
    miles_since_fuel = Fraction(0)
    segments: list[Segment] = []
    completed = 0  # number of milestones whose on-duty activity has been performed
    stop: CycleStop | None = None

    def remaining() -> int:
        return c.CYCLE_LIMIT_MIN - cycle

    def append(
        status: Status, kind: Kind, minutes: int, dist: Fraction = Fraction(0), note: str = ""
    ) -> None:
        nonlocal t, pos
        segments.append(Segment(t, t + minutes, status, kind, float(pos), float(pos + dist), note))
        t += minutes
        pos += dist

    def try_on_duty(kind: Kind, minutes: int, note: str = "") -> bool:
        """Schedule an atomic ON activity. False (no side effect) if it does not fit (A-17)."""
        nonlocal cycle, drive_since_break, window_open
        if minutes > remaining():
            return False
        if window_open is None:
            window_open = t
        append(Status.ON, kind, minutes, note=note)
        cycle += minutes
        if minutes >= c.BREAK_MIN:  # HOS-4: an activity >= 30 min satisfies the break on its own
            drive_since_break = 0
        return True

    def try_begin_shift() -> bool:
        """Every duty period starts with a pre-trip (A-7); it also opens the 14 h window."""
        nonlocal drive_shift
        if not try_on_duty(Kind.PRETRIP, params.pretrip_min, "Pre-trip inspection"):
            return False
        drive_shift = 0
        return True

    def try_rest_10h() -> bool:
        """False (no side effect) rather than a dangling rest: the next shift needs a pre-trip
        plus at least 1 minute of driving (hos-rules.md section 7.3)."""
        nonlocal drive_shift, drive_since_break, window_open
        if remaining() < params.pretrip_min + 1:
            return False
        append(Status.SB, Kind.REST, c.RESET_MIN, note="10-hour rest")
        drive_shift = 0
        drive_since_break = 0
        window_open = None
        return True

    def do_restart() -> None:
        """The internal, default-off option (D-2): zero the cycle and every shift clock."""
        nonlocal cycle, drive_shift, drive_since_break, window_open
        append(Status.OFF, Kind.RESTART, c.RESTART_MIN, note="34-hour restart")
        cycle = 0
        drive_shift = 0
        drive_since_break = 0
        window_open = None
        # miles_since_fuel is untouched: a restart is about the clock, not the fuel tank.

    # --- the initial pre-trip, before any milestone ---------------------------------------------
    while not try_begin_shift():
        if not params.allow_34_hour_restart:
            stop = _make_stop(
                Blocked.PRETRIP, completed, milestones, t, pos, route_miles, speed, remaining()
            )
            break
        do_restart()
        # loop retries try_begin_shift(); a freshly reset cycle always covers one pre-trip.

    # --- pickup, then drop-off --------------------------------------------------------------------
    if stop is None:
        for idx, (kind, target_miles, duration) in enumerate(milestones):
            while True:  # retried once per restart, if the internal option is on
                blocked: Blocked | None = None
                while pos < target_miles:
                    r = remaining()
                    if r <= 0:
                        blocked = Blocked.DRIVE
                        break
                    if drive_shift >= c.DRIVE_LIMIT_MIN or (
                        window_open is not None and t >= window_open + c.WINDOW_MIN
                    ):
                        if try_rest_10h():
                            if not try_begin_shift():  # pragma: no cover - see guarantee above
                                blocked = Blocked.PRETRIP
                                break
                            continue
                        blocked = Blocked.NEXT_SHIFT
                        break
                    if miles_since_fuel >= fuel_interval:
                        if try_on_duty(Kind.FUEL, params.fuel_stop_min, "Fuel"):
                            miles_since_fuel = Fraction(0)
                            continue
                        blocked = Blocked.FUEL
                        break
                    if drive_since_break >= c.BREAK_DRIVE_LIMIT_MIN:
                        append(Status.OFF, Kind.BREAK, c.BREAK_MIN, note="30-minute break")
                        drive_since_break = 0
                        continue

                    remaining_miles = target_miles - pos
                    window_cap = (
                        window_open + c.WINDOW_MIN - t if window_open is not None else math.inf
                    )
                    n = min(
                        math.ceil(remaining_miles * c.MINUTES_PER_HOUR / speed),
                        c.DRIVE_LIMIT_MIN - drive_shift,
                        c.BREAK_DRIVE_LIMIT_MIN - drive_since_break,
                        window_cap,
                        r,
                        math.floor((fuel_interval - miles_since_fuel) * c.MINUTES_PER_HOUR / speed),
                    )
                    if n <= 0:
                        # Less than a mile remains before the fuel cap floors to 0 minutes;
                        # fuelling a little early is still "at least every 1,000 mi" (FUEL-1).
                        if try_on_duty(Kind.FUEL, params.fuel_stop_min, "Fuel"):
                            miles_since_fuel = Fraction(0)
                            continue
                        blocked = Blocked.FUEL
                        break

                    n = int(n)
                    dist = min(Fraction(n) * speed / c.MINUTES_PER_HOUR, remaining_miles)
                    append(Status.D, Kind.DRIVE, n, dist)
                    drive_shift += n
                    drive_since_break += n
                    cycle += n  # D-1: driving consumes the 70-hour allowance too
                    miles_since_fuel += dist

                if blocked is None:
                    if try_on_duty(kind, duration, _MILESTONE_NOTE[kind]):
                        completed = idx + 1
                        break  # this milestone is done; the outer for-loop moves to the next one
                    blocked = _MILESTONE_BLOCKED[kind]

                if not params.allow_34_hour_restart:
                    stop = _make_stop(
                        blocked, completed, milestones, t, pos, route_miles, speed, remaining()
                    )
                    break
                do_restart()
                if not try_begin_shift():  # pragma: no cover - see guarantee above
                    stop = _make_stop(
                        Blocked.PRETRIP,
                        completed,
                        milestones,
                        t,
                        pos,
                        route_miles,
                        speed,
                        remaining(),
                    )
                    break
                # retry this same milestone from the top of the `while True`

            if stop is not None:
                break

    status = PlanStatus.CYCLE_EXHAUSTED if stop is not None else PlanStatus.COMPLETE
    return PlanResult(
        departure=departure,
        carry_in_min=cycle_used_min,
        route_miles=float(route_miles),
        segments=tuple(segments),
        status=status,
        stop=stop,
    )


def _make_stop(
    blocked: Blocked,
    completed: int,
    milestones: list[tuple[Kind, Fraction, int]],
    minute: int,
    pos: Fraction,
    route_miles: Fraction,
    speed: Fraction,
    remaining_min: int,
) -> CycleStop:
    """Build the ``CycleStop`` for hos-rules.md section 7.4, including the ``shortfall_min``
    lower bound: driving the unplanned miles plus every pending milestone, minus what is left."""
    pending = tuple(kind for kind, _, _ in milestones[completed:])
    unplanned = route_miles - pos
    drive_needed = math.ceil(unplanned * c.MINUTES_PER_HOUR / speed) if unplanned > 0 else 0
    pending_activity = sum(duration for _, _, duration in milestones[completed:])
    shortfall = drive_needed + pending_activity - remaining_min
    return CycleStop(
        minute=minute,
        mile=float(pos),
        blocked=blocked,
        pending=pending,
        unplanned_miles=float(unplanned),
        shortfall_min=shortfall,
    )
