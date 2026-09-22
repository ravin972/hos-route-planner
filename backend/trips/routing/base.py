"""The routing/geocoding abstraction (architecture.md section 4.3, decision D-7).

Every provider adapter implements one of the two Protocols here. ``trips.hos`` never sees any of
this -- ``services.py`` (Phase 3) is the only place that hands the HOS engine plain leg distances,
never a ``Route``, a ``Place`` or a provider error. Enforced by ``trips/tests/test_architecture.py``
(the import-graph guard).

The typed errors are the adapter boundary architecture.md section 4.4 describes: every provider
failure becomes one of these, never a raw ``requests`` exception leaking past the adapter. The
comment on each names the HTTP status and error `code` it is documented to eventually become in
``trips/api/errors.py`` (Phase 3) -- this module does not do that mapping itself.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Place:
    """A resolved or geocoded location."""

    label: str
    lat: float
    lng: float


@dataclass(frozen=True)
class RouteStep:
    """One turn-by-turn instruction (architecture.md section 6.2's ``legs[].steps[]``)."""

    instruction: str
    distance_mi: float
    road: str


@dataclass(frozen=True)
class RouteLeg:
    """One leg of the trip: current->pickup, or pickup->dropoff."""

    from_place: Place
    to_place: Place
    distance_mi: float
    steps: tuple[RouteStep, ...]


@dataclass(frozen=True)
class Route:
    """A routed path through all waypoints, in order."""

    geometry: str  # encoded polyline, precision 5 (architecture.md section 6.2)
    bounds: tuple[
        tuple[float, float], tuple[float, float]
    ]  # (min_lat, min_lng), (max_lat, max_lng)
    legs: tuple[RouteLeg, ...]
    distance_mi: float


class RoutingError(Exception):
    """Base of every typed routing-provider failure. Never raised directly."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UpstreamError(RoutingError):
    """The provider returned 5xx, a 429, or a response this adapter could not parse.
    Eventually HTTP 502 ``upstream_error`` (architecture.md section 4.4)."""


class UpstreamTimeoutError(RoutingError):
    """The provider did not respond within the configured connect/read timeout, even after the
    one retry. Eventually HTTP 504 ``upstream_timeout``."""


class UnroutableError(RoutingError):
    """No drivable route exists between the given points. Eventually HTTP 422 ``unroutable``."""


class OutOfCoverageError(RoutingError):
    """The route exceeds the provider's own limits (for example, > 6,000 km) or a point is not
    road-connected. Eventually HTTP 422 ``out_of_coverage``."""


class RoutingService(Protocol):
    """Turns an ordered list of (lat, lng) waypoints into a routed path.

    ``trips.hos`` never calls this -- only ``services.py`` does, and only to obtain plain leg
    distances in miles before the HOS engine ever runs.
    """

    def route(self, waypoints: Sequence[tuple[float, float]]) -> Route: ...


class GeocodingService(Protocol):
    """Typeahead / forward geocoding, US results only (decision AD-6)."""

    def search(self, query: str, *, limit: int = 5) -> list[Place]: ...
