"""The OpenRouteService adapter (architecture.md AD-5, decisions Q14/D-7).

Verified against HeiGIT's current documentation on 2026-09-22 (Phase 2), not carried over from
memory: the current host is ``https://api.heigit.org/openrouteservice``, the ``v2`` directions
endpoint takes the API key as a plain ``Authorization`` header (not a query parameter -- that was
only ever true of the old, now-irrelevant v1 API), and ``driving-hgv`` is a documented profile with
published limits of 6,000 km and 50 waypoints. The deprecated ``api.openrouteservice.org`` host is
never used here.

``ORS_API_KEY`` is read from the environment only in ``from_env()`` below -- never hardcoded,
logged, or placed in a request URL where it could end up in an access log.
"""

import os
from collections.abc import Sequence
from typing import Any

import requests

from .base import (
    OutOfCoverageError,
    Place,
    Route,
    RouteLeg,
    RouteStep,
    UnroutableError,
    UpstreamError,
    UpstreamTimeoutError,
)

DEFAULT_BASE_URL = "https://api.heigit.org/openrouteservice"
PROFILE = "driving-hgv"
CONNECT_TIMEOUT_S = 3.0
READ_TIMEOUT_S = 10.0
METERS_PER_MILE = 1609.344
# See routing/photon.py's USER_AGENT comment: some providers block the requests library's default
# User-Agent as an anti-bot measure. No evidence ORS does this, but a real, identifiable
# User-Agent is good API citizenship and costs nothing.
USER_AGENT = "spotter-hos-planner/0.1 (assessment project; contact via repository)"

# Documented ORS internal error codes (giscience.github.io/openrouteservice error-codes reference)
# that mean "no route" or "point not found" rather than a generic provider failure.
_UNROUTABLE_CODES = {2009, 2010, 6010, 8010}


def _as_float(value: object) -> float:
    """A response field typed as ``object`` (untrusted JSON) that must actually be numeric."""
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    raise UpstreamError(f"ORS response field is not numeric: {value!r}")


class OpenRouteServiceAdapter:
    """A ``RoutingService`` backed by OpenRouteService's ``driving-hgv`` directions endpoint."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        connect_timeout: float = CONNECT_TIMEOUT_S,
        read_timeout: float = READ_TIMEOUT_S,
        session: requests.Session | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must not be empty")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = (connect_timeout, read_timeout)
        self._session = session or requests.Session()
        # See routing/photon.py: requests.Session() pre-populates User-Agent itself at
        # construction, so setdefault() would be a no-op here -- this must overwrite.
        self._session.headers["User-Agent"] = USER_AGENT

    def route(self, waypoints: Sequence[tuple[float, float]]) -> Route:
        """``waypoints`` are (lat, lng) pairs, in trip order (current, pickup, dropoff, ...)."""
        if len(waypoints) < 2:
            raise ValueError("route() needs at least 2 waypoints")

        url = f"{self._base_url}/v2/directions/{PROFILE}"
        body = {
            "coordinates": [[lng, lat] for lat, lng in waypoints],  # ORS wants [lng, lat]
            "instructions": True,
        }
        data = self._post(url, body)
        return self._parse_route(data, waypoints)

    def _post(self, url: str, body: dict[str, Any]) -> dict[str, object]:
        headers = {"Authorization": self._api_key, "Content-Type": "application/json"}
        last_error: Exception | None = None

        for _attempt in range(2):  # one retry, since a directions request has no side effects
            try:
                response = self._session.post(
                    url, json=body, headers=headers, timeout=self._timeout
                )
            except requests.Timeout as exc:
                last_error = exc
                continue
            except requests.RequestException as exc:
                last_error = exc
                continue

            if response.status_code == 200:
                try:
                    result = response.json()
                except ValueError as exc:
                    raise UpstreamError(f"ORS returned a non-JSON 200 response: {exc}") from exc
                if not isinstance(result, dict):
                    got = type(result).__name__
                    raise UpstreamError(
                        f"ORS returned a JSON response that is not an object: {got}"
                    )
                return result

            self._raise_for_error_response(response)

        if isinstance(last_error, requests.Timeout):
            raise UpstreamTimeoutError(
                f"ORS did not respond within {self._timeout}s (after 1 retry)"
            ) from last_error
        raise UpstreamError(f"could not reach ORS: {last_error}") from last_error

    def _raise_for_error_response(self, response: requests.Response) -> None:
        code: int | None = None
        message = response.text[:300]
        try:
            payload = response.json()
            if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
                error = payload["error"]
                code = error.get("code")
                message = str(error.get("message", message))
        except ValueError:
            pass  # non-JSON error body; fall through with the raw text

        if code in _UNROUTABLE_CODES:
            raise UnroutableError(f"ORS could not route between the given points: {message}")
        if response.status_code == 422:
            raise OutOfCoverageError(f"ORS rejected the request as out of coverage: {message}")
        raise UpstreamError(f"ORS returned HTTP {response.status_code}: {message}")

    def _parse_route(
        self, data: dict[str, object], waypoints: Sequence[tuple[float, float]]
    ) -> Route:
        try:
            routes = data["routes"]
            if not isinstance(routes, list) or not routes:
                raise UpstreamError("ORS response has no routes")
            route = routes[0]
            bbox = route["bbox"]  # [min_lng, min_lat, max_lng, max_lat]
            geometry = route["geometry"]
            distance_m = route["summary"]["distance"]
            segments = route["segments"]

            if not isinstance(segments, list) or len(segments) != len(waypoints) - 1:
                got = len(segments) if isinstance(segments, list) else "non-list"
                raise UpstreamError(
                    f"ORS returned {got} segment(s) for {len(waypoints) - 1} leg(s)"
                )

            legs = tuple(
                self._parse_leg(seg, waypoints[i], waypoints[i + 1])
                for i, seg in enumerate(segments)
            )
        except (KeyError, TypeError, IndexError) as exc:
            raise UpstreamError(f"ORS response is missing an expected field: {exc}") from exc

        return Route(
            geometry=str(geometry),
            bounds=((bbox[1], bbox[0]), (bbox[3], bbox[2])),
            legs=legs,
            distance_mi=float(distance_m) / METERS_PER_MILE,
        )

    @staticmethod
    def _parse_leg(
        segment: dict[str, object], from_wp: tuple[float, float], to_wp: tuple[float, float]
    ) -> RouteLeg:
        steps_data = segment.get("steps", [])
        if not isinstance(steps_data, list):
            steps_data = []
        steps = tuple(
            RouteStep(
                instruction=str(s.get("instruction", "")),
                distance_mi=_as_float(s.get("distance", 0.0)) / METERS_PER_MILE,
                road=str(s.get("name") or ""),
            )
            for s in steps_data
            if isinstance(s, dict)
        )
        return RouteLeg(
            from_place=Place("", from_wp[0], from_wp[1]),
            to_place=Place("", to_wp[0], to_wp[1]),
            distance_mi=_as_float(segment["distance"]) / METERS_PER_MILE,
            steps=steps,
        )


def from_env() -> OpenRouteServiceAdapter:
    """Build the adapter from ``ORS_API_KEY`` (required) and ``ORS_BASE_URL`` (optional).

    The only place in this codebase that reads ``ORS_API_KEY`` -- callers never see the value.
    """
    api_key = os.environ.get("ORS_API_KEY", "")
    if not api_key:
        raise RuntimeError("ORS_API_KEY is not set")
    base_url = os.environ.get("ORS_BASE_URL", DEFAULT_BASE_URL)
    return OpenRouteServiceAdapter(api_key=api_key, base_url=base_url)
