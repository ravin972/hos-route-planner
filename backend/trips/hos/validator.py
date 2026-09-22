"""The independent, minute-stepping validator (hos-rules.md section 10, decision D-6).

Written differently from the planner on purpose: it imports only the limit values from
``constants.py`` and the dataclasses from ``types.py``, never calls a planner function, and steps
through the finished timeline one minute at a time instead of event by event. It never trusts a
segment's ``kind`` label to decide whether a reset happened -- resets are derived from ``status``
alone, exactly like a real inspector reading the grid. Two dissimilar implementations agreeing on
the same plan is the project's main defence against a bug both would otherwise share.

``validate()``'s parameters extend hos-rules.md's illustrative ``validate(segments, carry_in_min,
params)`` sketch with two additions, neither of which changes a rule: ``departure`` is required
because ``V_GAP`` must know where the timeline should start even when ``segments`` is empty (S5a:
nothing fits, so there is nothing to derive it from), and ``daily_logs`` is an optional keyword
because ``V_DAY_1440`` checks the padded, day-sliced output of ``logs.py`` -- padding is added
there (hos-rules.md section 9.1), never by the planner -- and this module must not import that
package to compute it.
"""

from collections.abc import Sequence

from . import constants as c
from .types import DailyLog, Kind, PlanParams, Segment, Status, Violation, ViolationCode

_VALID_STATUSES = frozenset(s.value for s in Status)
_VALID_KINDS = frozenset(k.value for k in Kind)


def _structural_violations(segments: Sequence[Segment], departure: int) -> list[Violation]:
    """V_STATUS, V_INTEGER, V_OVERLAP and V_GAP.

    Checked before any minute-stepping: that loop assumes a well-formed, contiguous, sorted,
    integer-minute timeline, and this function is what guarantees the assumption -- or explains
    exactly why it does not hold -- instead of the loop crashing or misbehaving on bad input.
    """
    violations: list[Violation] = []

    for seg in segments:
        start_ok = type(seg.start) is int
        end_ok = type(seg.end) is int
        if not (start_ok and end_ok):
            violations.append(
                Violation(
                    ViolationCode.INTEGER,
                    None,
                    f"segment boundary is not an int minute: start={seg.start!r} end={seg.end!r}",
                )
            )
        if str(seg.status) not in _VALID_STATUSES:
            violations.append(
                Violation(ViolationCode.STATUS, None, f"unknown duty status {seg.status!r}")
            )
        if str(seg.kind) not in _VALID_KINDS:
            violations.append(
                Violation(ViolationCode.STATUS, None, f"unknown segment kind {seg.kind!r}")
            )
        if not (start_ok and end_ok and seg.end > seg.start):
            violations.append(
                Violation(
                    ViolationCode.STATUS,
                    seg.start if start_ok else None,
                    f"segment has non-positive duration: {seg.start} to {seg.end}",
                )
            )

    if not segments:
        return violations

    ordered = sorted(segments, key=lambda s: s.start)
    if list(ordered) != list(segments):
        violations.append(
            Violation(ViolationCode.STATUS, None, "segments are not in chronological order")
        )

    if ordered[0].start != departure:
        violations.append(
            Violation(
                ViolationCode.GAP,
                ordered[0].start,
                f"the timeline does not start at departure ({departure}); "
                f"the first segment starts at {ordered[0].start}",
            )
        )

    for prev, nxt in zip(ordered, ordered[1:], strict=False):
        if prev.end > nxt.start:
            violations.append(
                Violation(
                    ViolationCode.OVERLAP,
                    nxt.start,
                    f"segment ending at {prev.end} overlaps the next one, which starts at "
                    f"{nxt.start}",
                )
            )
        elif prev.end < nxt.start:
            violations.append(
                Violation(
                    ViolationCode.GAP,
                    prev.end,
                    f"gap in the timeline between {prev.end} and {nxt.start}",
                )
            )

    return violations


def _timeline_violations(
    segments: Sequence[Segment], carry_in_min: int, params: PlanParams
) -> list[Violation]:
    """The eight HOS-rule checks, walked one minute at a time over a *known-well-formed* timeline.

    State mirrors hos-rules.md section 6, plus two independent run counters it names but keeps
    implicit: ``nondrive_run`` (OFF, SB or ON -- any non-driving status; broken only by D; backs
    the 30-minute-interruption clock, HOS-4) and ``rest_run`` (OFF or SB *only*; broken by ON or D
    too; backs the 10-hour reset, HOS-1, and the 34-hour restart / cycle reset, HOS-6). A real
    reset is derived purely from ``status`` -- never from a segment's ``kind`` label.
    """
    violations: list[Violation] = []

    window_open: int | None = None
    drive_shift = 0
    drive_since_break = 0
    nondrive_run = 0
    rest_run = 0
    carry_in_component = carry_in_min
    day_totals: dict[int, int] = {}
    miles_since_fuel = 0.0

    def cycle_after(day: int) -> int:
        rolling = sum(v for d, v in day_totals.items() if d > day - c.CYCLE_DAYS)
        return carry_in_component + rolling

    for seg in segments:
        is_drive = seg.status == Status.D
        per_minute_miles = seg.miles / seg.minutes if is_drive else 0.0

        for i in range(seg.minutes):
            t = seg.start + i
            day = t // c.MINUTES_PER_DAY
            on_duty_minute = False

            if is_drive:
                if drive_shift >= c.DRIVE_LIMIT_MIN:
                    violations.append(
                        Violation(
                            ViolationCode.DRIVE_11,
                            t,
                            f"driving minute {t} starts with {drive_shift} min already driven "
                            f"since the last reset (limit {c.DRIVE_LIMIT_MIN})",
                        )
                    )
                if window_open is not None and t >= window_open + c.WINDOW_MIN:
                    violations.append(
                        Violation(
                            ViolationCode.WINDOW_14,
                            t,
                            f"driving minute {t} starts at or after the 14-hour window closes "
                            f"at {window_open + c.WINDOW_MIN}",
                        )
                    )
                if drive_since_break >= c.BREAK_DRIVE_LIMIT_MIN:
                    violations.append(
                        Violation(
                            ViolationCode.BREAK_30,
                            t,
                            f"driving minute {t} starts with {drive_since_break} min driven "
                            f"since the last qualifying break (limit {c.BREAK_DRIVE_LIMIT_MIN})",
                        )
                    )

            if window_open is None and seg.status in (Status.ON, Status.D):
                window_open = t

            if is_drive:
                drive_shift += 1
                drive_since_break += 1
                nondrive_run = 0
                rest_run = 0
                miles_since_fuel += per_minute_miles
                on_duty_minute = True
            elif seg.status == Status.ON:
                nondrive_run += 1
                rest_run = 0
                if nondrive_run >= c.BREAK_MIN:
                    drive_since_break = 0
                on_duty_minute = True
            else:  # OFF or SB
                nondrive_run += 1
                if nondrive_run >= c.BREAK_MIN:
                    drive_since_break = 0
                rest_run += 1
                if rest_run >= c.RESET_MIN:
                    drive_shift = 0
                    window_open = None
                if rest_run >= c.RESTART_MIN:
                    carry_in_component = 0
                    day_totals.clear()

            if on_duty_minute:
                day_totals[day] = day_totals.get(day, 0) + 1
                cycle = cycle_after(day)
                if cycle > c.CYCLE_LIMIT_MIN:
                    violations.append(
                        Violation(
                            ViolationCode.CYCLE_70,
                            t,
                            f"on-duty minute {t} brings the trailing {c.CYCLE_DAYS}-day on-duty "
                            f"total to {cycle} min (limit {c.CYCLE_LIMIT_MIN})",
                        )
                    )

        if seg.kind == Kind.FUEL:
            if miles_since_fuel > params.fuel_interval_miles + c.MILE_TOLERANCE:
                violations.append(
                    Violation(
                        ViolationCode.FUEL_1000,
                        seg.start,
                        f"{miles_since_fuel:.3f} mi driven since the last fuel stop before "
                        f"refuelling at minute {seg.start} (limit {params.fuel_interval_miles})",
                    )
                )
            miles_since_fuel = 0.0
        elif is_drive and miles_since_fuel > params.fuel_interval_miles + c.MILE_TOLERANCE:
            violations.append(
                Violation(
                    ViolationCode.FUEL_1000,
                    seg.end,
                    f"{miles_since_fuel:.3f} mi driven since the last fuel stop by minute "
                    f"{seg.end} (limit {params.fuel_interval_miles})",
                )
            )

        if seg.kind == Kind.REST and seg.minutes < c.RESET_MIN:
            violations.append(
                Violation(
                    ViolationCode.RESET_10,
                    seg.start,
                    f"a 'rest' segment at minute {seg.start} is only {seg.minutes} min, needs "
                    f"at least {c.RESET_MIN}",
                )
            )

        if seg.kind == Kind.RESTART:
            if not params.allow_34_hour_restart:
                violations.append(
                    Violation(
                        ViolationCode.RESTART_34,
                        seg.start,
                        "a 'restart' segment exists but allow_34_hour_restart is False",
                    )
                )
            if seg.minutes < c.RESTART_MIN:
                violations.append(
                    Violation(
                        ViolationCode.RESTART_34,
                        seg.start,
                        f"a 'restart' segment at minute {seg.start} is only {seg.minutes} min, "
                        f"needs at least {c.RESTART_MIN}",
                    )
                )

    return violations


def validate_daily_logs(daily_logs: Sequence[DailyLog]) -> list[Violation]:
    """V_DAY_1440: every log covers exactly 1,440 minutes, contiguously, with no gaps/overlaps."""
    violations: list[Violation] = []
    for log in daily_logs:
        segs = log.segments
        total = sum(s.minutes for s in segs)
        if total != c.MINUTES_PER_DAY:
            violations.append(
                Violation(
                    ViolationCode.DAY_1440,
                    None,
                    f"day {log.day_number} (index {log.day_index}) sums to {total} min, "
                    f"not {c.MINUTES_PER_DAY}",
                )
            )
            continue
        cursor = 0
        contiguous = True
        for s in segs:
            if s.start_min != cursor:
                contiguous = False
                break
            cursor = s.end_min
        if not contiguous or cursor != c.MINUTES_PER_DAY:
            violations.append(
                Violation(
                    ViolationCode.DAY_1440,
                    None,
                    f"day {log.day_number} (index {log.day_index}) has gaps or overlaps between "
                    "its segments despite summing to 1,440 min",
                )
            )
    return violations


def validate(
    segments: Sequence[Segment],
    carry_in_min: int,
    params: PlanParams,
    departure: int,
    *,
    daily_logs: Sequence[DailyLog] | None = None,
) -> list[Violation]:
    """Check a finished plan against all twelve rules in hos-rules.md section 10.

    Runs the eight timeline-content checks (``V_DRIVE_11`` ... ``V_FUEL_1000``) only when the
    timeline is structurally sound (see ``_structural_violations``): minute-stepping over a plan
    with an unrepaired gap, overlap, non-integer boundary or unknown status is not well-defined,
    so this returns just the structural findings instead of guessing through them. ``V_DAY_1440``
    only runs when ``daily_logs`` is supplied.
    """
    structural = _structural_violations(segments, departure)
    if structural:
        return structural

    violations = _timeline_violations(segments, carry_in_min, params)
    if daily_logs is not None:
        violations.extend(validate_daily_logs(daily_logs))
    return violations
