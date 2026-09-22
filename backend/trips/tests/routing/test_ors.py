"""``trips.routing.ors``: mocked success and every documented failure mode.

Every HTTP call is mocked with ``responses`` -- no real network reaches ORS in this file. The one
opt-in live call lives in ``test_live.py``.
"""

import requests
import responses as responses_lib

from trips.routing.base import (
    OutOfCoverageError,
    UnroutableError,
    UpstreamError,
    UpstreamTimeoutError,
)
from trips.routing.ors import DEFAULT_BASE_URL, PROFILE, OpenRouteServiceAdapter, from_env

URL = f"{DEFAULT_BASE_URL}/v2/directions/{PROFILE}"

# A realistic success body, shaped exactly as the v2 JSON directions response is documented:
# top-level routes[]/bbox/metadata; routes[].summary/geometry/bbox/segments[].steps[].
SUCCESS_BODY = {
    "routes": [
        {
            "summary": {"distance": 482803.2, "duration": 17280.0},  # 300.0 mi exactly
            "geometry": "kv~jE~cqcO_ulLxpsA",
            "bbox": [-90.1994, 32.7767, -87.6298, 41.8781],
            "segments": [
                {
                    "distance": 482803.2,
                    "duration": 17280.0,
                    "steps": [
                        {
                            "distance": 1609.344,
                            "duration": 120.0,
                            "instruction": "Head south on Main St",
                            "name": "Main St",
                        },
                        {
                            "distance": 481193.856,
                            "duration": 17160.0,
                            "instruction": "Continue on I-55 S",
                            "name": "I-55",
                        },
                    ],
                },
            ],
        }
    ],
    "bbox": [-90.1994, 32.7767, -87.6298, 41.8781],
    "metadata": {},
}
WAYPOINTS = [(41.8781, -87.6298), (32.7767, -96.7970)]


@responses_lib.activate
def test_successful_route_is_parsed_correctly() -> None:
    responses_lib.add(responses_lib.POST, URL, json=SUCCESS_BODY, status=200)
    adapter = OpenRouteServiceAdapter(api_key="test-key")

    route = adapter.route(WAYPOINTS)

    assert route.distance_mi == 300.0
    assert route.geometry == "kv~jE~cqcO_ulLxpsA"
    assert route.bounds == ((32.7767, -90.1994), (41.8781, -87.6298))
    assert len(route.legs) == 1
    assert route.legs[0].distance_mi == 300.0
    assert len(route.legs[0].steps) == 2
    assert route.legs[0].steps[0].road == "Main St"
    assert route.legs[0].steps[0].distance_mi == 1.0


@responses_lib.activate
def test_the_authorization_header_and_body_are_sent_correctly() -> None:
    responses_lib.add(responses_lib.POST, URL, json=SUCCESS_BODY, status=200)
    adapter = OpenRouteServiceAdapter(api_key="my-secret-key")

    adapter.route(WAYPOINTS)

    sent = responses_lib.calls[0].request
    assert sent.headers["Authorization"] == "my-secret-key"
    assert sent.headers["Content-Type"] == "application/json"
    assert sent.url == URL
    import json

    body = json.loads(sent.body)
    # ORS wants [lng, lat] -- the opposite order from this codebase's (lat, lng) convention
    assert body["coordinates"] == [[-87.6298, 41.8781], [-96.7970, 32.7767]]


@responses_lib.activate
def test_never_uses_the_deprecated_host() -> None:
    """A structural guard: nothing in this adapter can construct a request to the old host."""
    adapter = OpenRouteServiceAdapter(api_key="test-key")
    assert "api.openrouteservice.org" not in DEFAULT_BASE_URL
    assert DEFAULT_BASE_URL == "https://api.heigit.org/openrouteservice"
    assert adapter._base_url == DEFAULT_BASE_URL


@responses_lib.activate
def test_uses_driving_hgv_profile() -> None:
    responses_lib.add(responses_lib.POST, URL, json=SUCCESS_BODY, status=200)
    OpenRouteServiceAdapter(api_key="test-key").route(WAYPOINTS)
    assert "/driving-hgv" in responses_lib.calls[0].request.url


@responses_lib.activate
def test_http_429_is_mapped_to_upstream_error() -> None:
    responses_lib.add(responses_lib.POST, URL, json={"error": {"code": 5}}, status=429)
    adapter = OpenRouteServiceAdapter(api_key="test-key")
    try:
        adapter.route(WAYPOINTS)
        raise AssertionError("expected UpstreamError")
    except UpstreamError as exc:
        assert "429" in exc.message


@responses_lib.activate
def test_http_500_is_mapped_to_upstream_error() -> None:
    responses_lib.add(responses_lib.POST, URL, body="internal server error", status=500)
    adapter = OpenRouteServiceAdapter(api_key="test-key")
    try:
        adapter.route(WAYPOINTS)
        raise AssertionError("expected UpstreamError")
    except UpstreamError as exc:
        assert "500" in exc.message


@responses_lib.activate
def test_connection_timeout_is_mapped_to_upstream_timeout_error_after_one_retry() -> None:
    responses_lib.add(responses_lib.POST, URL, body=requests.exceptions.ConnectTimeout())
    responses_lib.add(responses_lib.POST, URL, body=requests.exceptions.ConnectTimeout())
    adapter = OpenRouteServiceAdapter(api_key="test-key")
    try:
        adapter.route(WAYPOINTS)
        raise AssertionError("expected UpstreamTimeoutError")
    except UpstreamTimeoutError:
        pass
    assert len(responses_lib.calls) == 2  # confirms exactly one retry, not zero and not many


@responses_lib.activate
def test_malformed_response_is_mapped_to_upstream_error() -> None:
    responses_lib.add(responses_lib.POST, URL, json={"routes": [{"summary": {}}]}, status=200)
    adapter = OpenRouteServiceAdapter(api_key="test-key")
    try:
        adapter.route(WAYPOINTS)
        raise AssertionError("expected UpstreamError")
    except UpstreamError as exc:
        assert "missing" in exc.message.lower()


@responses_lib.activate
def test_non_json_response_body_is_mapped_to_upstream_error() -> None:
    responses_lib.add(responses_lib.POST, URL, body="<html>not json</html>", status=200)
    adapter = OpenRouteServiceAdapter(api_key="test-key")
    try:
        adapter.route(WAYPOINTS)
        raise AssertionError("expected UpstreamError")
    except UpstreamError:
        pass


@responses_lib.activate
def test_unroutable_error_code_is_mapped_to_unroutable_error() -> None:
    """ORS internal code 2009: 'Route could not be found between locations'."""
    responses_lib.add(
        responses_lib.POST,
        URL,
        json={"error": {"code": 2009, "message": "Route could not be found between locations"}},
        status=404,
    )
    adapter = OpenRouteServiceAdapter(api_key="test-key")
    try:
        adapter.route(WAYPOINTS)
        raise AssertionError("expected UnroutableError")
    except UnroutableError as exc:
        assert "locations" in exc.message


@responses_lib.activate
def test_422_without_a_known_unroutable_code_is_out_of_coverage() -> None:
    responses_lib.add(
        responses_lib.POST,
        URL,
        json={"error": {"code": 3099, "message": "Distance exceeds maximum"}},
        status=422,
    )
    adapter = OpenRouteServiceAdapter(api_key="test-key")
    try:
        adapter.route(WAYPOINTS)
        raise AssertionError("expected OutOfCoverageError")
    except OutOfCoverageError as exc:
        assert "maximum" in exc.message


def test_constructor_rejects_an_empty_api_key() -> None:
    import pytest

    with pytest.raises(ValueError):
        OpenRouteServiceAdapter(api_key="")


def test_route_rejects_fewer_than_2_waypoints() -> None:
    import pytest

    adapter = OpenRouteServiceAdapter(api_key="test-key")
    with pytest.raises(ValueError):
        adapter.route([(0.0, 0.0)])


def test_from_env_requires_ors_api_key(monkeypatch) -> None:  # noqa: ANN001
    import pytest

    monkeypatch.delenv("ORS_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ORS_API_KEY"):
        from_env()


def test_from_env_reads_the_key_and_uses_the_verified_default_host(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("ORS_API_KEY", "env-key")
    monkeypatch.delenv("ORS_BASE_URL", raising=False)
    adapter = from_env()
    assert adapter._api_key == "env-key"
    assert adapter._base_url == DEFAULT_BASE_URL


def test_from_env_honours_a_custom_ors_base_url(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("ORS_API_KEY", "env-key")
    monkeypatch.setenv("ORS_BASE_URL", "https://example.test/openrouteservice")
    adapter = from_env()
    assert adapter._base_url == "https://example.test/openrouteservice"
