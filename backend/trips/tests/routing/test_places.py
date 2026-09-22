"""``trips.routing.places``: the offline nearest-place lookup."""

from trips.routing.places import (
    NamedPlace,
    PlaceIndex,
    default_index,
    load_places,
    nearest_place_label,
)


def test_default_index_loads_the_committed_csv() -> None:
    idx = default_index()
    assert isinstance(idx, PlaceIndex)
    assert len(load_places()) > 0


def test_nearest_finds_the_exact_point() -> None:
    places = [
        NamedPlace("Chicago", "IL", 41.8781, -87.6298),
        NamedPlace("Dallas", "TX", 32.7767, -96.7970),
    ]
    idx = PlaceIndex(places)
    assert idx.nearest(41.8781, -87.6298).name == "Chicago"
    assert idx.nearest(32.7767, -96.7970).name == "Dallas"


def test_nearest_picks_the_closer_of_two() -> None:
    places = [NamedPlace("A", "XX", 0.0, 0.0), NamedPlace("B", "XX", 10.0, 10.0)]
    idx = PlaceIndex(places)
    assert idx.nearest(0.5, 0.5).name == "A"
    assert idx.nearest(9.5, 9.5).name == "B"


def test_nearest_expands_search_radius_when_the_local_cell_is_empty() -> None:
    """A single far-away place, queried from an empty grid cell -- must still be found via the
    widening-ring search, not silently return nothing."""
    places = [NamedPlace("Remote", "XX", 45.0, -100.0)]
    idx = PlaceIndex(places)
    found = idx.nearest(0.0, 0.0)
    assert found.name == "Remote"


def test_place_index_rejects_empty_input() -> None:
    import pytest

    with pytest.raises(ValueError):
        PlaceIndex([])


def test_named_place_label_format() -> None:
    assert NamedPlace("Chicago", "IL", 41.8781, -87.6298).label == "Chicago, IL"


def test_nearest_place_label_on_a_known_city() -> None:
    assert nearest_place_label(41.8781, -87.6298) == "Chicago, IL"


def test_nearest_place_label_falls_back_to_coordinates_when_nothing_is_close() -> None:
    label = nearest_place_label(0.0, 0.0)  # the Gulf of Guinea -- nowhere near any US place
    assert label.startswith("near ")
    assert "0.00" in label
