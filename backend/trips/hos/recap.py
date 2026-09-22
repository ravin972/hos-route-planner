"""The recap block of the daily log (hos-rules.md sections 9.4 and 3.2, decision D-1).

Box A is "on duty last 8 days including today" and box B is 70 hours minus A (the docx gives a
single scalar for "current cycle used" with no day-by-day breakdown, so no 8-day roll-off is
modelled for it -- A-13). Box C needs a day-by-day history the assessment does not provide, so it
stays ``None`` per the still-open Q7 clarification (hos-rules.md section 9.4) -- never guess it.
"""

from collections.abc import Sequence

from . import constants as c
from .types import Recap, Segment, Status


def cycle_used_by_end_of_day(segments: Sequence[Segment], carry_in_min: int) -> dict[int, int]:
    """Box A's value as of 24:00 of every day the (unpadded) plan segments touch.

    Walks minute by minute so a reset landing mid-segment is attributed to the day it actually
    completes in, not the day the long rest-status segment merely starts. A 34-hour restart can
    span parts of three calendar days (the S4b golden: day 2 is entirely inside the restart and
    still shows the pre-reset total, since only 1,920 of the 2,040 minutes have elapsed by
    midnight; day 3, where the 2,040th minute falls early in the morning, shows 0 plus whatever is
    scheduled afterwards). This mirrors the reset rule in ``validator.py`` -- both compute the same
    real-world quantity -- but it is bookkeeping for display, not a second independent HOS check
    (D-6 is specifically about the planner and the validator), so a small, obviously-correct repeat
    of the arithmetic here is fine; the golden tests check this value directly either way.
    """
    result: dict[int, int] = {}
    cycle = carry_in_min
    rest_run = 0
    for seg in segments:
        is_rest = seg.status in (Status.OFF, Status.SB)
        on_duty = seg.status in (Status.D, Status.ON)
        for i in range(seg.minutes):
            t = seg.start + i
            if is_rest:
                rest_run += 1
                if rest_run >= c.RESTART_MIN:
                    cycle = 0
            else:
                rest_run = 0
                if on_duty:
                    cycle += 1
            result[t // c.MINUTES_PER_DAY] = cycle
    return result


def build_recap(on_duty_today_min: int, cycle_used_min: int) -> Recap:
    """Box A is handed in already resolved by ``cycle_used_by_end_of_day``; this fills box B."""
    available = max(0, c.CYCLE_LIMIT_MIN - cycle_used_min)
    return Recap(
        on_duty_today_min=on_duty_today_min,
        cycle_used_min=cycle_used_min,
        available_min=available,
    )
