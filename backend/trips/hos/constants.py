"""Every number the HOS engine uses (hos-rules.md sections 3.2 and 5).

Durations and limits are whole minutes (rule M-1, decision D-4). Only miles and the planning speed
are fractional. ``trips/tests/hos/test_constants.py`` asserts that these values equal the literals
printed in hos-rules.md, so the document and the code cannot drift apart silently.
"""

from typing import Final

MINUTES_PER_HOUR: Final = 60
MINUTES_PER_DAY: Final = 24 * MINUTES_PER_HOUR

# --- Limits (hos-rules.md section 5) ---------------------------------------------------------
RESET_MIN: Final = 10 * MINUTES_PER_HOUR  # HOS-1: consecutive OFF/SB minutes that reset a shift
DRIVE_LIMIT_MIN: Final = 11 * MINUTES_PER_HOUR  # HOS-2: driving minutes per shift
WINDOW_MIN: Final = 14 * MINUTES_PER_HOUR  # HOS-3: the window never pauses
BREAK_DRIVE_LIMIT_MIN: Final = 8 * MINUTES_PER_HOUR  # HOS-4: cumulative driving before a break
BREAK_MIN: Final = 30  # HOS-4: the non-driving run that interrupts it
CYCLE_LIMIT_MIN: Final = 70 * MINUTES_PER_HOUR  # HOS-5: on-duty minutes (product constraint, D-1)
RESTART_MIN: Final = 34 * MINUTES_PER_HOUR  # HOS-6: consecutive OFF/SB minutes that zero the cycle
CYCLE_DAYS: Final = 8  # the cycle is a rolling sum over this many log days
FUEL_INTERVAL_MILES: Final = 1000  # FUEL-1: the docx's "fuel at least every 1,000 miles"

# --- Assumptions (hos-rules.md section 3.2) --------------------------------------------------
PICKUP_MIN: Final = 60  # A-1
DROPOFF_MIN: Final = 60  # A-2
FUEL_STOP_MIN: Final = 30  # A-4
PRETRIP_MIN: Final = 15  # A-6, performed at the start of every shift (A-7)
DEFAULT_AVG_SPEED_MPH: Final = 55  # A-8 / D-5: the single documented default
MAX_AVG_SPEED_MPH: Final = 80  # A-8: the planning speed is positive and at most this

# --- Technical ---------------------------------------------------------------------------------
# The validator compares miles reported as floats; anything within a millimetre is equal.
MILE_TOLERANCE: Final = 1e-6
