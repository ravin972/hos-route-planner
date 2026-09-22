"""Domain types of the HOS engine.

Everything is a frozen dataclass. Every time value is an ``int`` number of minutes on one timeline
whose day ``d`` spans minutes ``d * 1440`` to ``(d + 1) * 1440`` (rule M-1, decision D-4); miles are
``float``. ``Segment`` is deliberately unvalidated: the independent validator has to be able to look
at bad data and say so, so validation of a *plan* lives there and validation of *inputs* lives in
``PlanParams`` and ``planner.plan``.
"""

import math
from dataclasses import dataclass
from enum import StrEnum

from . import constants as c


class Status(StrEnum):
    """The four rows of the log grid (hos-rules.md section 4)."""

    OFF = "OFF"
    SB = "SB"
    D = "D"
    ON = "ON"


class Kind(StrEnum):
    """What a segment is. ``restart`` only appears with the internal 34-hour option (D-2)."""

    PRETRIP = "pretrip"
    DRIVE = "drive"
    PICKUP = "pickup"
    DROPOFF = "dropoff"
    FUEL = "fuel"
    BREAK = "break"
    REST = "rest"
    RESTART = "restart"
    IDLE = "idle"


class PlanStatus(StrEnum):
    COMPLETE = "complete"
    CYCLE_EXHAUSTED = "cycle_exhausted"


class Blocked(StrEnum):
    """The step that did not fit when the 70-hour allowance ran out (hos-rules.md section 7.4)."""

    PRETRIP = "pretrip"
    DRIVE = "drive"
    FUEL = "fuel"
    PICKUP = "pickup"
    DROPOFF = "dropoff"
    NEXT_SHIFT = "next_shift"


class ViolationCode(StrEnum):
    """The twelve validator checks (hos-rules.md section 10)."""

    DRIVE_11 = "V_DRIVE_11"
    WINDOW_14 = "V_WINDOW_14"
    BREAK_30 = "V_BREAK_30"
    RESET_10 = "V_RESET_10"
    CYCLE_70 = "V_CYCLE_70"
    RESTART_34 = "V_RESTART_34"
    FUEL_1000 = "V_FUEL_1000"
    DAY_1440 = "V_DAY_1440"
    OVERLAP = "V_OVERLAP"
    GAP = "V_GAP"
    INTEGER = "V_INTEGER"
    STATUS = "V_STATUS"


def _require_minutes(name: str, value: object) -> int:
    """A positive whole number of minutes; floats and bools are refused (rule M-1)."""
    if type(value) is not int:
        raise TypeError(f"{name} must be an int number of minutes, not {type(value).__name__}")
    if value < 1:
        raise ValueError(f"{name} must be at least 1 minute, got {value}")
    return value


def _require_positive_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{name} must be a number, not {type(value).__name__}")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number, got {value}")
    return float(value)


@dataclass(frozen=True)
class PlanParams:
    """Everything configurable about a plan (hos-rules.md section 3.2, decision D-5).

    ``allow_34_hour_restart`` is the internal, default-off option of decision D-2. It is not exposed
    through the API, the environment or the UI.
    """

    avg_speed_mph: float = c.DEFAULT_AVG_SPEED_MPH
    pretrip_min: int = c.PRETRIP_MIN
    pickup_min: int = c.PICKUP_MIN
    dropoff_min: int = c.DROPOFF_MIN
    fuel_stop_min: int = c.FUEL_STOP_MIN
    fuel_interval_miles: float = c.FUEL_INTERVAL_MILES
    allow_34_hour_restart: bool = False

    def __post_init__(self) -> None:
        speed = _require_positive_number("avg_speed_mph", self.avg_speed_mph)
        if speed > c.MAX_AVG_SPEED_MPH:
            raise ValueError(f"avg_speed_mph must be at most {c.MAX_AVG_SPEED_MPH}, got {speed}")
        _require_positive_number("fuel_interval_miles", self.fuel_interval_miles)
        durations = [
            _require_minutes("pretrip_min", self.pretrip_min),
            _require_minutes("pickup_min", self.pickup_min),
            _require_minutes("dropoff_min", self.dropoff_min),
            _require_minutes("fuel_stop_min", self.fuel_stop_min),
        ]
        # After a restart the pre-trip and then any one on-duty step must fit a fresh cycle;
        # otherwise the restart option could loop forever on an impossible request.
        if self.pretrip_min + max(durations[1:]) > c.CYCLE_LIMIT_MIN:
            raise ValueError(
                "a pre-trip plus the longest on-duty stop must fit in one 70-hour cycle"
            )
        if not isinstance(self.allow_34_hour_restart, bool):
            raise TypeError("allow_34_hour_restart must be a bool")


@dataclass(frozen=True)
class Segment:
    """One stretch of a single duty status on the trip timeline (minutes, ``end`` exclusive)."""

    start: int
    end: int
    status: Status
    kind: Kind
    pos_start: float
    pos_end: float
    note: str = ""

    @property
    def minutes(self) -> int:
        return self.end - self.start

    @property
    def miles(self) -> float:
        return self.pos_end - self.pos_start


@dataclass(frozen=True)
class CycleStop:
    """Where and why scheduling stopped because the 70-hour allowance ran out (section 7.4)."""

    minute: int
    mile: float
    blocked: Blocked
    pending: tuple[Kind, ...]
    unplanned_miles: float
    shortfall_min: int


@dataclass(frozen=True)
class PlanResult:
    """The planner's answer: an ordered, contiguous list of segments starting at ``departure``."""

    departure: int
    carry_in_min: int
    route_miles: float
    segments: tuple[Segment, ...]
    status: PlanStatus
    stop: CycleStop | None

    @property
    def end(self) -> int:
        """The minute after the last scheduled activity (``departure`` if nothing fit)."""
        return self.segments[-1].end if self.segments else self.departure


@dataclass(frozen=True)
class Violation:
    code: ViolationCode
    minute: int | None
    message: str


# --- Daily logs (hos-rules.md section 9) ----------------------------------------------------------


@dataclass(frozen=True)
class LogSegment:
    """A segment clipped to one log day; minutes are minute-of-day, 0 to 1,440."""

    start_min: int
    end_min: int
    status: Status
    kind: Kind
    pos_start: float
    pos_end: float
    note: str = ""

    @property
    def minutes(self) -> int:
        return self.end_min - self.start_min

    @property
    def miles(self) -> float:
        return self.pos_end - self.pos_start


@dataclass(frozen=True)
class Remark:
    """One change of duty status. The place name is added later, from ``mile``."""

    minute: int
    status: Status
    kind: Kind
    mile: float
    note: str


@dataclass(frozen=True)
class DutyTotals:
    """Minutes per grid row; they always add up to 1,440 for a log day."""

    off: int
    sb: int
    d: int
    on: int

    @property
    def total(self) -> int:
        return self.off + self.sb + self.d + self.on

    @property
    def on_duty(self) -> int:
        return self.d + self.on


@dataclass(frozen=True)
class Recap:
    """The form's recap block. C (the last 5 days) is not collected, so it stays ``None`` (Q7)."""

    on_duty_today_min: int
    cycle_used_min: int  # A: carry-in plus every on-duty minute up to 24:00
    available_min: int  # B: 70 hours minus A
    last_5_days_min: int | None = None


@dataclass(frozen=True)
class DailyLog:
    """One 24-hour log sheet: contiguous segments covering minutes 0 to 1,440."""

    day_index: int  # calendar day on the trip timeline, ``t // 1440``
    day_number: int  # 1-based position in the trip
    segments: tuple[LogSegment, ...]
    totals: DutyTotals
    miles: float
    remarks: tuple[Remark, ...]
    recap: Recap
