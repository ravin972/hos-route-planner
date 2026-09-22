"""Opt-in live smoke tests against the real ORS and Photon services.

implementation-plan.md section 4.1: "Live smoke | pytest -m live | 2 tests against real ORS /
Photon (opt-in, needs key) | manual / CI-off". Never runs by default -- only with `pytest -m live`
-- and the ORS test skips cleanly (not a failure) when `ORS_API_KEY` is not set, which is the
case in this environment right now. Nothing here is mocked; a failure here means the real,
current provider behavior differs from what the adapter assumes.
"""

import os

import pytest

from trips.routing.ors import from_env as ors_from_env
from trips.routing.photon import PhotonAdapter

pytestmark = pytest.mark.live


def test_live_ors_route_chicago_to_st_louis() -> None:
    if not os.environ.get("ORS_API_KEY"):
        pytest.skip("ORS_API_KEY is not set in this environment")

    adapter = ors_from_env()
    route = adapter.route([(41.8781, -87.6298), (38.6270, -90.1994)])  # Chicago -> St. Louis

    assert route.distance_mi > 250  # real-road distance is ~300 mi; a loose sanity bound
    assert route.distance_mi < 400
    assert route.geometry
    assert len(route.legs) == 1
    assert route.legs[0].steps  # real turn-by-turn instructions came back


def test_live_photon_search_finds_chicago() -> None:
    adapter = PhotonAdapter()
    places = adapter.search("Chicago, Illinois")

    assert places, "Photon returned no results for a well-known US city"
    assert all(p.lat and p.lng for p in places)
