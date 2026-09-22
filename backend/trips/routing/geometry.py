"""Polyline codec, haversine distance, and the mile -> (lat, lng) index (architecture.md 4.1, 4.2).

The Google/ORS encoded-polyline algorithm at precision 5 (architecture.md section 6.2: "encoded
polyline, precision 5, simplified"). Pure Python, no dependency: the algorithm is ~20 lines and a
library would be more overhead than the code it replaces.
"""

import math
from collections.abc import Sequence

EARTH_RADIUS_MI = 3958.7613
DEFAULT_PRECISION = 5
MAX_DISPLAY_POINTS = 5000


def decode_polyline(encoded: str, precision: int = DEFAULT_PRECISION) -> list[tuple[float, float]]:
    """Decode an encoded polyline into (lat, lng) points."""
    factor = 10**precision
    coords: list[tuple[float, float]] = []
    index = 0
    lat = 0
    lng = 0
    length = len(encoded)

    while index < length:
        for is_lat in (True, False):
            shift = 0
            result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else (result >> 1)
            if is_lat:
                lat += delta
            else:
                lng += delta
        coords.append((lat / factor, lng / factor))

    return coords


def encode_polyline(
    points: Sequence[tuple[float, float]], precision: int = DEFAULT_PRECISION
) -> str:
    """Encode (lat, lng) points into a polyline string (the inverse of ``decode_polyline``)."""
    factor = 10**precision
    out: list[str] = []
    prev_lat = 0
    prev_lng = 0

    for lat, lng in points:
        ilat = round(lat * factor)
        ilng = round(lng * factor)
        out.append(_encode_value(ilat - prev_lat))
        out.append(_encode_value(ilng - prev_lng))
        prev_lat, prev_lng = ilat, ilng

    return "".join(out)


def _encode_value(value: int) -> str:
    value = ~(value << 1) if value < 0 else (value << 1)
    chunks: list[str] = []
    while value >= 0x20:
        chunks.append(chr((0x20 | (value & 0x1F)) + 63))
        value >>= 5
    chunks.append(chr(value + 63))
    return "".join(chunks)


def haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in miles between two (lat, lng) points."""
    lat1, lng1 = math.radians(a[0]), math.radians(a[1])
    lat2, lng2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(min(1.0, math.sqrt(h)))


def simplify(
    points: Sequence[tuple[float, float]], max_points: int = MAX_DISPLAY_POINTS
) -> list[tuple[float, float]]:
    """Decimate to at most ``max_points``, always keeping the first and last point.

    A uniform stride, not Douglas-Peucker: real US highway routes from ORS rarely approach the
    ~5,000-point ceiling architecture.md sets, so a simple, obviously-correct decimation is enough
    -- this only ever runs on the rare very-long route, and only for the *display* copy of the
    geometry (the mile index is always built from the full-resolution points).
    """
    n = len(points)
    if n <= max_points:
        return list(points)
    stride = math.ceil(n / max_points)
    kept = list(points[::stride])
    if kept[-1] != points[-1]:
        kept.append(points[-1])
    return kept


class MileIndex:
    """Maps a route mile to a (lat, lng) coordinate, for placing stop markers along the route.

    architecture.md section 4.2 step 4: "Build the mile->coordinate index from the full-resolution
    geometry (cumulative haversine, scaled to the provider's total distance)." Haversine (straight
    great-circle hops between consecutive shape points) slightly undercounts a curving road, so
    the cumulative distances are rescaled to match the provider's own reported total -- the
    index's last point is always exactly ``total_distance_mi``, what the HOS engine planned to.
    """

    def __init__(self, points: Sequence[tuple[float, float]], total_distance_mi: float) -> None:
        if len(points) < 2:
            raise ValueError("MileIndex needs at least 2 points")
        cumulative = [0.0]
        for a, b in zip(points, points[1:], strict=False):  # deliberately offset by 1 -- see below
            cumulative.append(cumulative[-1] + haversine_miles(a, b))

        raw_total = cumulative[-1]
        scale = total_distance_mi / raw_total if raw_total > 0 else 1.0
        self._miles = [c * scale for c in cumulative]
        self._points = list(points)
        self._total = total_distance_mi

    def at(self, mile: float) -> tuple[float, float]:
        """The interpolated (lat, lng) at ``mile`` along the route (clamped to [0, total])."""
        mile = max(0.0, min(mile, self._total))
        miles = self._miles

        lo, hi = 0, len(miles) - 1
        while lo < hi - 1:
            mid = (lo + hi) // 2
            if miles[mid] <= mile:
                lo = mid
            else:
                hi = mid

        span = miles[hi] - miles[lo]
        frac = (mile - miles[lo]) / span if span > 0 else 0.0
        lat = self._points[lo][0] + frac * (self._points[hi][0] - self._points[lo][0])
        lng = self._points[lo][1] + frac * (self._points[hi][1] - self._points[lo][1])
        return (lat, lng)
