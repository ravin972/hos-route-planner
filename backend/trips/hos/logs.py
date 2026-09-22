"""Slice a finished plan into 24-hour daily logs (hos-rules.md section 9).

Padding (day 1's OFF before departure, A-10; the last day's OFF to midnight, A-11) is added here,
not by the planner -- ``plan()``'s segments cover only ``departure`` to the end of scheduling.
"""

from collections.abc import Sequence

from . import constants as c
from .recap import build_recap, cycle_used_by_end_of_day
from .types import DailyLog, DutyTotals, Kind, LogSegment, PlanResult, Remark, Segment, Status

_ACTIVITY_LABEL: dict[Kind, str] = {
    Kind.DRIVE: "Driving",
    Kind.IDLE: "Off duty",
}


def _label(seg: Segment) -> str:
    """A human-readable activity description for a remark. Place names are added later (Phase 3,
    from the offline nearest-place lookup) -- this module never resolves a location."""
    return seg.note or _ACTIVITY_LABEL.get(seg.kind, seg.kind.value.replace("_", " ").title())


def _padded_timeline(segments: Sequence[Segment], departure: int) -> list[Segment]:
    """Day 1's OFF-before-departure pad (A-10) and the last day's OFF-to-midnight pad (A-11).

    If nothing was ever scheduled (S5a: the cycle wall is hit before the first pre-trip fits),
    both pads apply and together cover one whole day of OFF, matching hos-rules.md's "Day 1 =
    OFF 24" for that case.
    """
    padded: list[Segment] = []
    day_start = (departure // c.MINUTES_PER_DAY) * c.MINUTES_PER_DAY
    if departure > day_start:
        padded.append(Segment(day_start, departure, Status.OFF, Kind.IDLE, 0.0, 0.0))
    padded.extend(segments)

    end = segments[-1].end if segments else departure
    end_pos = segments[-1].pos_end if segments else 0.0
    day_end = (
        end if end % c.MINUTES_PER_DAY == 0 else (end // c.MINUTES_PER_DAY + 1) * c.MINUTES_PER_DAY
    )
    if day_end > end:
        padded.append(Segment(end, day_end, Status.OFF, Kind.IDLE, end_pos, end_pos))
    return padded


def build_daily_logs(result: PlanResult) -> list[DailyLog]:
    """Build one ``DailyLog`` per calendar day the padded plan touches.

    Totals and the drawn segments both come from the same padded, clipped segment list (never
    computed separately), so they can never disagree -- hos-rules.md section 9.2 and property 4.
    A segment that crosses midnight is split, with its miles apportioned by the fraction of its
    minutes on each side (constant speed within a drive segment, by construction of the planner).
    """
    padded = _padded_timeline(result.segments, result.departure)
    if not padded:
        return []

    first_day = padded[0].start // c.MINUTES_PER_DAY
    last_day = (padded[-1].end - 1) // c.MINUTES_PER_DAY
    cycle_by_day = cycle_used_by_end_of_day(result.segments, result.carry_in_min)

    logs: list[DailyLog] = []
    for day_number, day_index in enumerate(range(first_day, last_day + 1), start=1):
        day_start = day_index * c.MINUTES_PER_DAY
        day_end = day_start + c.MINUTES_PER_DAY

        log_segments: list[LogSegment] = []
        remarks: list[Remark] = []
        for seg in padded:
            lo = max(seg.start, day_start)
            hi = min(seg.end, day_end)
            if lo >= hi:
                continue
            if seg.miles != 0:
                frac_lo = (lo - seg.start) / seg.minutes
                frac_hi = (hi - seg.start) / seg.minutes
                pos_lo = seg.pos_start + frac_lo * seg.miles
                pos_hi = seg.pos_start + frac_hi * seg.miles
            else:
                pos_lo = pos_hi = seg.pos_start
            log_segments.append(
                LogSegment(
                    lo - day_start, hi - day_start, seg.status, seg.kind, pos_lo, pos_hi, seg.note
                )
            )
            if day_start <= seg.start < day_end:
                remarks.append(
                    Remark(seg.start - day_start, seg.status, seg.kind, seg.pos_start, _label(seg))
                )

        totals = DutyTotals(
            off=sum(s.minutes for s in log_segments if s.status == Status.OFF),
            sb=sum(s.minutes for s in log_segments if s.status == Status.SB),
            d=sum(s.minutes for s in log_segments if s.status == Status.D),
            on=sum(s.minutes for s in log_segments if s.status == Status.ON),
        )
        miles = sum(s.miles for s in log_segments if s.status == Status.D)
        cycle_used = cycle_by_day.get(day_index, result.carry_in_min)
        recap = build_recap(totals.on_duty, cycle_used)

        logs.append(
            DailyLog(
                day_index=day_index,
                day_number=day_number,
                segments=tuple(log_segments),
                totals=totals,
                miles=miles,
                remarks=tuple(remarks),
                recap=recap,
            )
        )
    return logs
