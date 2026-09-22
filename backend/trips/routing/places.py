"""Offline nearest-populated-place lookup for log remarks (architecture.md AD-7, hos-rules.md
section 9.3: every duty-status change needs a "nearest city, town, or village and State" label).

Loads ``trips/routing/data/us_places.csv`` (built by ``scripts/build_places.py``) into a simple
1-degree grid index: nearest-neighbor search checks the query point's cell and its 8 neighbors
first (almost always sufficient for a populated-places dataset), expanding outward only if none of
those cells hold a place -- never a full linear scan except on a pathologically sparse dataset.
"""

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .geometry import haversine_miles

DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "us_places.csv"
GRID_DEGREES = 1.0


@dataclass(frozen=True)
class NamedPlace:
    name: str
    state: str
    lat: float
    lng: float

    @property
    def label(self) -> str:
        return f"{self.name}, {self.state}"


class PlaceIndex:
    """Nearest-place lookup over a fixed set of ``NamedPlace``s."""

    def __init__(self, places: Iterable[NamedPlace]) -> None:
        self._places = list(places)
        if not self._places:
            raise ValueError("PlaceIndex needs at least one place")
        self._grid: dict[tuple[int, int], list[NamedPlace]] = {}
        for p in self._places:
            self._grid.setdefault(self._cell(p.lat, p.lng), []).append(p)

    @staticmethod
    def _cell(lat: float, lng: float) -> tuple[int, int]:
        return (int(lat // GRID_DEGREES), int(lng // GRID_DEGREES))

    def nearest(self, lat: float, lng: float) -> NamedPlace:
        """The nearest place to ``(lat, lng)``. Never returns nothing: falls back to a full scan
        of every place if no cell within a widening search radius holds one (architecture.md
        AD-13: fail loudly only when there is truly nothing to fall back to)."""
        cy, cx = self._cell(lat, lng)
        for radius in range(0, 6):
            candidates = [
                p
                for dy in range(-radius, radius + 1)
                for dx in range(-radius, radius + 1)
                if max(abs(dy), abs(dx)) == radius  # only the new outer ring each time
                for p in self._grid.get((cy + dy, cx + dx), [])
            ]
            if candidates:
                return min(candidates, key=lambda p: haversine_miles((lat, lng), (p.lat, p.lng)))
        return min(self._places, key=lambda p: haversine_miles((lat, lng), (p.lat, p.lng)))


def load_places(path: Path = DEFAULT_DATA_PATH) -> list[NamedPlace]:
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            NamedPlace(row["name"], row["state"], float(row["lat"]), float(row["lng"]))
            for row in reader
        ]


_default_index: PlaceIndex | None = None


def default_index() -> PlaceIndex:
    """The index over the committed CSV, built once and reused (it never changes at runtime)."""
    global _default_index
    if _default_index is None:
        _default_index = PlaceIndex(load_places())
    return _default_index


def nearest_place_label(lat: float, lng: float) -> str:
    """``"City, ST"`` for the nearest known place, or a coordinate fallback if none is close
    enough to be meaningful (architecture.md AD-13: never a blank place name)."""
    place = default_index().nearest(lat, lng)
    if haversine_miles((lat, lng), (place.lat, place.lng)) > 50:
        return f"near {lat:.2f}, {lng:.2f}"
    return place.label
