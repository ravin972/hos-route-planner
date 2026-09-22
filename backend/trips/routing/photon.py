"""The Photon geocoding/typeahead adapter (architecture.md AD-6).

Minimum integration for Phase 2: search-by-query only. Caching, debouncing and the
``GET /api/locations/search`` proxy endpoint that will actually call this are Phase 3/4 work
(architecture.md's own risk register, R-4, places caching and debounce at the frontend/API layer,
not here). Nominatim is never used -- its policy forbids typeahead (AD-6).
"""

from collections.abc import Sequence

import requests

from .base import Place, UpstreamError, UpstreamTimeoutError

DEFAULT_BASE_URL = "https://photon.komoot.io"
CONNECT_TIMEOUT_S = 3.0
READ_TIMEOUT_S = 10.0
# Verified live (Phase 2 G3 spike): Komoot's nginx returns a bare 403 for requests' own default
# User-Agent ("python-requests/x.y.z") specifically -- an anti-bot measure -- while any other
# reasonable value, including this one, succeeds. Without this, the adapter cannot reach the real
# service at all, even though every mocked test still passes.
USER_AGENT = "spotter-hos-planner/0.1 (assessment project; contact via repository)"


class PhotonAdapter:
    """A ``GeocodingService`` backed by Photon, filtered to US results (decision AD-6)."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        connect_timeout: float = CONNECT_TIMEOUT_S,
        read_timeout: float = READ_TIMEOUT_S,
        session: requests.Session | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = (connect_timeout, read_timeout)
        self._session = session or requests.Session()
        # requests.Session() pre-populates headers["User-Agent"] itself at construction time
        # (to "python-requests/x.y.z"), so setdefault() here would be a no-op -- this must
        # overwrite, not merely fill a gap. Verified live: this exact default value is what
        # Komoot's nginx blocks (see USER_AGENT's comment above).
        self._session.headers["User-Agent"] = USER_AGENT

    def search(self, query: str, *, limit: int = 5) -> list[Place]:
        if not query.strip():
            return []

        url = f"{self._base_url}/api/"
        params = {"q": query, "limit": str(limit), "lang": "en"}
        try:
            response = self._session.get(url, params=params, timeout=self._timeout)
        except requests.Timeout as exc:
            raise UpstreamTimeoutError(f"Photon did not respond within {self._timeout}s") from exc
        except requests.RequestException as exc:
            raise UpstreamError(f"could not reach Photon: {exc}") from exc

        if response.status_code != 200:
            raise UpstreamError(
                f"Photon returned HTTP {response.status_code}: {response.text[:300]}"
            )

        try:
            data = response.json()
            features = data["features"]
        except (ValueError, KeyError, TypeError) as exc:
            raise UpstreamError(
                f"Photon response is not a valid feature collection: {exc}"
            ) from exc
        if not isinstance(features, list):
            raise UpstreamError("Photon response 'features' is not a list")

        return [p for p in (self._to_place(f) for f in features) if p is not None]

    @staticmethod
    def _to_place(feature: object) -> Place | None:
        """US results only (AD-6); anything malformed or non-US is silently dropped, not an error
        -- a partial typeahead result list is a normal outcome, not a provider failure."""
        if not isinstance(feature, dict):
            return None
        geometry = feature.get("geometry")
        properties = feature.get("properties")
        if not isinstance(geometry, dict) or not isinstance(properties, dict):
            return None
        if properties.get("countrycode") != "US":
            return None

        coords = geometry.get("coordinates")
        if not isinstance(coords, Sequence) or len(coords) != 2:
            return None
        try:
            lng, lat = float(coords[0]), float(coords[1])
        except (TypeError, ValueError):
            return None

        raw_parts = [
            properties.get("name"),
            properties.get("city") or properties.get("county"),
            properties.get("state"),
        ]
        parts: list[str] = []
        for part in raw_parts:
            text = str(part) if part else ""
            if text and text != (parts[-1] if parts else None):  # drop an immediate duplicate
                parts.append(text)
        label = ", ".join(parts)
        if not label:
            return None
        return Place(label=label, lat=lat, lng=lng)


def from_env() -> PhotonAdapter:
    """Build the adapter from the optional ``PHOTON_BASE_URL`` (default: the public instance)."""
    import os

    base_url = os.environ.get("PHOTON_BASE_URL", DEFAULT_BASE_URL)
    return PhotonAdapter(base_url=base_url)
