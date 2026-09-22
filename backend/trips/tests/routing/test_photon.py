"""``trips.routing.photon``: mocked success, US-only filtering, and provider failures."""

import responses as responses_lib

from trips.routing.base import UpstreamError, UpstreamTimeoutError
from trips.routing.photon import DEFAULT_BASE_URL, PhotonAdapter, from_env

URL = f"{DEFAULT_BASE_URL}/api/"

FEATURE_COLLECTION = {
    "type": "FeatureCollection",
    "features": [
        {
            "geometry": {"type": "Point", "coordinates": [-87.6298, 41.8781]},
            "properties": {
                "name": "Chicago",
                "city": "Chicago",
                "state": "Illinois",
                "countrycode": "US",
            },
        },
        {
            "geometry": {"type": "Point", "coordinates": [-79.0, 43.0]},
            "properties": {"name": "Toronto", "city": "Toronto", "countrycode": "CA"},
        },
        {
            "geometry": {"type": "Point", "coordinates": [-90.1994, 38.6270]},
            "properties": {
                "name": "St. Louis",
                "city": "St. Louis",
                "state": "Missouri",
                "countrycode": "US",
            },
        },
    ],
}


@responses_lib.activate
def test_successful_search_returns_us_only_places() -> None:
    responses_lib.add(responses_lib.GET, URL, json=FEATURE_COLLECTION, status=200)
    adapter = PhotonAdapter()

    places = adapter.search("chicago")

    assert len(places) == 2
    assert places[0].label == "Chicago, Illinois"  # name == city: deduplicated
    assert places[0].lat == 41.8781
    assert places[0].lng == -87.6298
    assert places[1].label == "St. Louis, Missouri"
    assert all(p.label != "Toronto" for p in places)  # non-US result dropped


@responses_lib.activate
def test_query_params_are_sent_correctly() -> None:
    responses_lib.add(responses_lib.GET, URL, json=FEATURE_COLLECTION, status=200)
    PhotonAdapter().search("chicago", limit=3)
    sent = responses_lib.calls[0].request
    assert "q=chicago" in sent.url
    assert "limit=3" in sent.url


def test_empty_query_returns_empty_list_without_a_network_call() -> None:
    adapter = PhotonAdapter()
    assert adapter.search("   ") == []


@responses_lib.activate
def test_http_500_is_mapped_to_upstream_error() -> None:
    responses_lib.add(responses_lib.GET, URL, body="internal error", status=500)
    adapter = PhotonAdapter()
    try:
        adapter.search("chicago")
        raise AssertionError("expected UpstreamError")
    except UpstreamError as exc:
        assert "500" in exc.message


@responses_lib.activate
def test_timeout_is_mapped_to_upstream_timeout_error() -> None:
    import requests

    responses_lib.add(responses_lib.GET, URL, body=requests.exceptions.ReadTimeout())
    adapter = PhotonAdapter()
    try:
        adapter.search("chicago")
        raise AssertionError("expected UpstreamTimeoutError")
    except UpstreamTimeoutError:
        pass


@responses_lib.activate
def test_malformed_response_is_mapped_to_upstream_error() -> None:
    responses_lib.add(responses_lib.GET, URL, json={"not_features": []}, status=200)
    adapter = PhotonAdapter()
    try:
        adapter.search("chicago")
        raise AssertionError("expected UpstreamError")
    except UpstreamError:
        pass


@responses_lib.activate
def test_a_malformed_individual_feature_is_dropped_not_fatal() -> None:
    responses_lib.add(
        responses_lib.GET,
        URL,
        json={
            "features": [{"geometry": None, "properties": {}}, FEATURE_COLLECTION["features"][0]]
        },
        status=200,
    )
    places = PhotonAdapter().search("chicago")
    assert len(places) == 1
    assert places[0].label == "Chicago, Illinois"


def test_from_env_uses_the_documented_default_host(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.delenv("PHOTON_BASE_URL", raising=False)
    adapter = from_env()
    assert adapter._base_url == DEFAULT_BASE_URL == "https://photon.komoot.io"


def test_from_env_honours_a_custom_photon_base_url(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("PHOTON_BASE_URL", "https://example.test")
    adapter = from_env()
    assert adapter._base_url == "https://example.test"
