"""Coordinate -> IANA time zone -> UTC offset (hos-rules.md A-15, architecture.md section 4.1).

Uses ``tzfpy`` (offline, no network, no dependencies of its own) rather than ``timezonefinder``
-- see the Phase 2 G3 report for the size comparison that decided this (tzfpy: ~3 MB, zero
dependencies; timezonefinder: ~1.2 MB plus a 32.7 MB data package plus numpy/h3/cffi/flatbuffers,
roughly 60-100+ MB total -- a meaningful difference against Vercel's Python bundle-size limit,
architecture.md AD-9).

This module only resolves; it does not decide what "departure" means. A-16's fixed 08:00-local
convention and A-15's "one fixed offset for the whole trip" rule are ``services.py``'s job
(Phase 3) -- this just answers "what zone is this point in" and "what is that zone's offset at a
given instant", as two small, independently testable pure functions.
"""

from datetime import datetime, timedelta

import tzfpy


class UnknownTimeZoneError(Exception):
    """No IANA zone could be resolved for the given coordinates (for example, open ocean).

    hos-rules.md section 2 scopes this app to "US contiguous roads" only, so a real geocoded US
    point should never hit this -- but a caller must not silently default to a fabricated zone
    (architecture.md AD-13: fail loudly, never silently).
    """


def iana_zone_for(lat: float, lng: float) -> str:
    """The IANA zone name containing ``(lat, lng)``."""
    name = tzfpy.get_tz(lng, lat)  # tzfpy takes (lng, lat), the opposite of this function's order
    if not name or name.startswith("Etc/GMT"):
        raise UnknownTimeZoneError(f"no IANA zone resolved for ({lat}, {lng})")
    return name


def utc_offset_at(zone_name: str, at: datetime) -> timedelta:
    """``zone_name``'s UTC offset at the instant ``at`` (which must be timezone-aware)."""
    from zoneinfo import ZoneInfo

    if at.tzinfo is None:
        raise ValueError("at must be timezone-aware")
    offset = at.astimezone(ZoneInfo(zone_name)).utcoffset()
    if offset is None:  # pragma: no cover - ZoneInfo always returns an offset for a real zone
        raise UnknownTimeZoneError(f"{zone_name!r} has no UTC offset at {at!r}")
    return offset
