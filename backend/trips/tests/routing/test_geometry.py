"""``trips.routing.geometry``: polyline codec, haversine, simplification, the mile index."""

import pytest

from trips.routing.geometry import (
    MileIndex,
    decode_polyline,
    encode_polyline,
    haversine_miles,
    simplify,
)

CHICAGO = (41.8781, -87.6298)
ST_LOUIS = (38.6270, -90.1994)
DALLAS = (32.7767, -96.7970)


def test_polyline_round_trips() -> None:
    points = [CHICAGO, (40.0, -89.0), ST_LOUIS, (35.0, -93.5), DALLAS]
    encoded = encode_polyline(points)
    decoded = decode_polyline(encoded)
    assert len(decoded) == len(points)
    for original, back in zip(points, decoded, strict=True):
        assert original[0] == pytest.approx(back[0], abs=1e-5)
        assert original[1] == pytest.approx(back[1], abs=1e-5)


def test_encode_polyline_is_deterministic() -> None:
    points = [CHICAGO, ST_LOUIS]
    assert encode_polyline(points) == encode_polyline(points)


def test_decode_empty_string_is_empty_list() -> None:
    assert decode_polyline("") == []


def test_haversine_known_distance() -> None:
    # Chicago -> St. Louis straight-line distance is well-known: roughly 257-265 mi
    d = haversine_miles(CHICAGO, ST_LOUIS)
    assert 250 < d < 270


def test_haversine_same_point_is_zero() -> None:
    assert haversine_miles(CHICAGO, CHICAGO) == pytest.approx(0.0, abs=1e-9)


def test_simplify_is_a_no_op_under_the_limit() -> None:
    points = [CHICAGO, ST_LOUIS, DALLAS]
    assert simplify(points, max_points=5000) == points


def test_simplify_decimates_and_keeps_first_and_last() -> None:
    points = [(0.0 + i * 0.001, 0.0) for i in range(6000)]
    result = simplify(points, max_points=5000)
    assert len(result) <= 5000
    assert result[0] == points[0]
    assert result[-1] == points[-1]


def test_mile_index_endpoints_are_exact() -> None:
    points = [CHICAGO, (39.5, -89.0), ST_LOUIS]
    idx = MileIndex(points, total_distance_mi=300.0)
    assert idx.at(0) == points[0]
    assert idx.at(300) == points[-1]


def test_mile_index_clamps_out_of_range_queries() -> None:
    points = [CHICAGO, ST_LOUIS]
    idx = MileIndex(points, total_distance_mi=300.0)
    assert idx.at(-50) == idx.at(0)
    assert idx.at(9999) == idx.at(300)


def test_mile_index_is_monotonic_along_the_route() -> None:
    """As mile increases, the interpolated point should move consistently toward the end --
    checked via non-decreasing haversine distance from the start point."""
    points = [CHICAGO, (39.5, -89.0), ST_LOUIS, (35.0, -93.5), DALLAS]
    total = sum(haversine_miles(a, b) for a, b in zip(points, points[1:], strict=False))
    idx = MileIndex(points, total_distance_mi=total)
    last_d = -1.0
    for mile in range(0, int(total) + 1, 10):
        d = haversine_miles(CHICAGO, idx.at(mile))
        assert d >= last_d - 1e-6
        last_d = d


def test_mile_index_requires_at_least_2_points() -> None:
    with pytest.raises(ValueError):
        MileIndex([CHICAGO], total_distance_mi=0.0)
