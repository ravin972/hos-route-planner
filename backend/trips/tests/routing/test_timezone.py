"""``trips.routing.timezone``: offline, no network, no mocking needed."""

from datetime import UTC, datetime

import pytest

from trips.routing.timezone import UnknownTimeZoneError, iana_zone_for, utc_offset_at


@pytest.mark.parametrize(
    ("label", "lat", "lng", "expected_zone"),
    [
        ("Chicago, IL", 41.8781, -87.6298, "America/Chicago"),
        ("St. Louis, MO", 38.6270, -90.1994, "America/Chicago"),
        ("Dallas, TX", 32.7767, -96.7970, "America/Chicago"),
        ("New York, NY", 40.7128, -74.0060, "America/New_York"),
        ("Los Angeles, CA", 34.0522, -118.2437, "America/Los_Angeles"),
        ("Phoenix, AZ", 33.4484, -112.0740, "America/Phoenix"),  # no DST -- a documented edge case
        ("Denver, CO", 39.7392, -104.9903, "America/Denver"),
    ],
)
def test_known_us_cities_resolve_to_the_correct_iana_zone(label, lat, lng, expected_zone) -> None:  # noqa: ANN001
    assert iana_zone_for(lat, lng) == expected_zone, label


def test_open_ocean_raises_unknown_time_zone_error_instead_of_guessing() -> None:
    """architecture.md AD-13: fail loudly, never silently invent a zone."""
    with pytest.raises(UnknownTimeZoneError):
        iana_zone_for(0.0, 0.0)


def test_utc_offset_at_a_known_date_for_chicago() -> None:
    # 2026-09-22 is during US daylight time: Chicago is UTC-5 (CDT)
    at = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)
    offset = utc_offset_at("America/Chicago", at)
    assert offset.total_seconds() == -5 * 3600


def test_utc_offset_at_requires_a_timezone_aware_datetime() -> None:
    with pytest.raises(ValueError, match="aware"):
        utc_offset_at("America/Chicago", datetime(2026, 9, 22, 12, 0))  # naive, no tzinfo


def test_phoenix_has_no_dst_shift_across_the_year() -> None:
    """Arizona doesn't observe DST -- documented as a specific edge case (risk R-7)."""
    winter = utc_offset_at("America/Phoenix", datetime(2026, 1, 15, 12, 0, tzinfo=UTC))
    summer = utc_offset_at("America/Phoenix", datetime(2026, 7, 15, 12, 0, tzinfo=UTC))
    assert winter == summer
    assert winter.total_seconds() == -7 * 3600
