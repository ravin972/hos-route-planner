"""``trips.routing.base``: the Protocols, data types, and the typed error hierarchy."""

import pytest

from trips.routing.base import (
    GeocodingService,
    OutOfCoverageError,
    Place,
    Route,
    RouteLeg,
    RouteStep,
    RoutingError,
    RoutingService,
    UnroutableError,
    UpstreamError,
    UpstreamTimeoutError,
)


@pytest.mark.parametrize(
    "exc_cls",
    [UpstreamError, UpstreamTimeoutError, UnroutableError, OutOfCoverageError],
)
def test_every_typed_error_is_a_routing_error_and_carries_its_message(
    exc_cls: type[RoutingError],
) -> None:
    err = exc_cls("something went wrong")
    assert isinstance(err, RoutingError)
    assert isinstance(err, Exception)
    assert err.message == "something went wrong"
    assert str(err) == "something went wrong"


def test_the_four_typed_errors_are_distinct_classes() -> None:
    classes = {UpstreamError, UpstreamTimeoutError, UnroutableError, OutOfCoverageError}
    assert len(classes) == 4
    # none is a subclass of another -- a caller can catch exactly the one it means to handle
    for a in classes:
        for b in classes:
            if a is not b:
                assert not issubclass(a, b)


def test_place_route_and_friends_are_frozen_dataclasses() -> None:
    place = Place(label="Chicago, IL", lat=41.8781, lng=-87.6298)
    with pytest.raises(AttributeError):
        place.lat = 0.0  # type: ignore[misc]

    step = RouteStep(instruction="Head south", distance_mi=0.4, road="Main St")
    leg = RouteLeg(from_place=place, to_place=place, distance_mi=1.0, steps=(step,))
    route = Route(geometry="abc", bounds=((0.0, 0.0), (1.0, 1.0)), legs=(leg,), distance_mi=1.0)
    with pytest.raises(AttributeError):
        route.distance_mi = 2.0  # type: ignore[misc]


def test_routing_service_and_geocoding_service_are_runtime_checkable_shapes() -> None:
    """A structural check, not an isinstance check (Protocol without @runtime_checkable) --
    confirms any adapter implementing these methods satisfies the Protocol at type-check time."""

    class FakeRouter:
        def route(self, waypoints):  # noqa: ANN001, ANN201 - shape-only fake
            raise NotImplementedError

    class FakeGeocoder:
        def search(self, query: str, *, limit: int = 5):  # noqa: ANN201 - shape-only fake
            raise NotImplementedError

    router: RoutingService = FakeRouter()
    geocoder: GeocodingService = FakeGeocoder()
    assert hasattr(router, "route")
    assert hasattr(geocoder, "search")
