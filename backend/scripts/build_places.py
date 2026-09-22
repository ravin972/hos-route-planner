"""Build ``trips/routing/data/us_places.csv`` (architecture.md AD-7 / section 4.1).

Two modes:

1. ``--source <geonames-extract.txt>``: the real path. Point it at a raw GeoNames tab-separated
   extract (the standard columns from ``allCountries.txt`` / ``US.txt`` -- geonameid, name,
   asciiname, alternatenames, latitude, longitude, feature class, feature code, country code, cc2,
   admin1 code, admin2 code, admin3 code, admin4 code, population, elevation, dem, timezone,
   modification date; https://download.geonames.org/export/dump/). Filters to feature class ``P``
   (populated places), country code ``US``, dedupes by (name, state), sorts, writes the CSV.
2. No ``--source``: **this environment has no network access to GeoNames' download server**, so
   this mode writes a curated, hand-verified seed list instead -- one or more real, well-known
   places per US state plus DC, real public coordinates (not GeoNames-derived, but not guessed
   either: state capitals and major metros are stable, unambiguous facts). This is a disclosed
   stand-in, not a hidden shortcut: the committed CSV in this repo was built this way. Re-run with
   ``--source`` and a real extract to get full GeoNames coverage.

Either way the output columns are identical: ``name,state,lat,lng``.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent / "trips" / "routing" / "data" / "us_places.csv"
)

# name, state (2-letter), lat, lng -- one or more well-known populated places per state + DC.
# Coordinates are each place's commonly published city-center latitude/longitude.
SEED_PLACES: list[tuple[str, str, float, float]] = [
    ("Montgomery", "AL", 32.3792, -86.3077),
    ("Birmingham", "AL", 33.5186, -86.8104),
    ("Huntsville", "AL", 34.7304, -86.5861),
    ("Mobile", "AL", 30.6954, -88.0399),
    ("Juneau", "AK", 58.3019, -134.4197),
    ("Anchorage", "AK", 61.2181, -149.9003),
    ("Fairbanks", "AK", 64.8378, -147.7164),
    ("Phoenix", "AZ", 33.4484, -112.0740),
    ("Tucson", "AZ", 32.2226, -110.9747),
    ("Flagstaff", "AZ", 35.1983, -111.6513),
    ("Mesa", "AZ", 33.4152, -111.8315),
    ("Little Rock", "AR", 34.7465, -92.2896),
    ("Fayetteville", "AR", 36.0626, -94.1574),
    ("Sacramento", "CA", 38.5816, -121.4944),
    ("Los Angeles", "CA", 34.0522, -118.2437),
    ("San Francisco", "CA", 37.7749, -122.4194),
    ("San Diego", "CA", 32.7157, -117.1611),
    ("Fresno", "CA", 36.7378, -119.7871),
    ("Bakersfield", "CA", 35.3733, -119.0187),
    ("Redding", "CA", 40.5865, -122.3917),
    ("Denver", "CO", 39.7392, -104.9903),
    ("Colorado Springs", "CO", 38.8339, -104.8214),
    ("Grand Junction", "CO", 39.0639, -108.5506),
    ("Pueblo", "CO", 38.2544, -104.6091),
    ("Hartford", "CT", 41.7658, -72.6734),
    ("Bridgeport", "CT", 41.1792, -73.1894),
    ("New Haven", "CT", 41.3083, -72.9279),
    ("Dover", "DE", 39.1582, -75.5244),
    ("Wilmington", "DE", 39.7391, -75.5398),
    ("Washington", "DC", 38.9072, -77.0369),
    ("Tallahassee", "FL", 30.4383, -84.2807),
    ("Jacksonville", "FL", 30.3322, -81.6557),
    ("Miami", "FL", 25.7617, -80.1918),
    ("Orlando", "FL", 28.5383, -81.3792),
    ("Tampa", "FL", 27.9506, -82.4572),
    ("Pensacola", "FL", 30.4213, -87.2169),
    ("Atlanta", "GA", 33.7490, -84.3880),
    ("Savannah", "GA", 32.0809, -81.0912),
    ("Augusta", "GA", 33.4735, -82.0105),
    ("Columbus", "GA", 32.4610, -84.9877),
    ("Honolulu", "HI", 21.3069, -157.8583),
    ("Hilo", "HI", 19.7241, -155.0868),
    ("Boise", "ID", 43.6150, -116.2023),
    ("Idaho Falls", "ID", 43.4917, -112.0339),
    ("Coeur d'Alene", "ID", 47.6777, -116.7805),
    ("Springfield", "IL", 39.7817, -89.6501),
    ("Chicago", "IL", 41.8781, -87.6298),
    ("Peoria", "IL", 40.6936, -89.5890),
    ("Rockford", "IL", 42.2711, -89.0940),
    ("Effingham", "IL", 39.1200, -88.5434),
    ("Indianapolis", "IN", 39.7684, -86.1581),
    ("Fort Wayne", "IN", 41.0793, -85.1394),
    ("South Bend", "IN", 41.6764, -86.2520),
    ("Evansville", "IN", 37.9748, -87.5558),
    ("Des Moines", "IA", 41.5868, -93.6250),
    ("Cedar Rapids", "IA", 41.9779, -91.6656),
    ("Davenport", "IA", 41.5236, -90.5776),
    ("Sioux City", "IA", 42.4963, -96.4049),
    ("Topeka", "KS", 39.0473, -95.6752),
    ("Wichita", "KS", 37.6872, -97.3301),
    ("Kansas City", "KS", 39.1147, -94.6275),
    ("Salina", "KS", 38.8403, -97.6114),
    ("Frankfort", "KY", 38.2009, -84.8733),
    ("Louisville", "KY", 38.2527, -85.7585),
    ("Lexington", "KY", 38.0406, -84.5037),
    ("Bowling Green", "KY", 36.9685, -86.4808),
    ("Baton Rouge", "LA", 30.4515, -91.1871),
    ("New Orleans", "LA", 29.9511, -90.0715),
    ("Shreveport", "LA", 32.5252, -93.7502),
    ("Lafayette", "LA", 30.2241, -92.0198),
    ("Augusta", "ME", 44.3106, -69.7795),
    ("Portland", "ME", 43.6591, -70.2568),
    ("Bangor", "ME", 44.8012, -68.7778),
    ("Annapolis", "MD", 38.9784, -76.4922),
    ("Baltimore", "MD", 39.2904, -76.6122),
    ("Hagerstown", "MD", 39.6418, -77.7200),
    ("Boston", "MA", 42.3601, -71.0589),
    ("Worcester", "MA", 42.2626, -71.8023),
    ("Springfield", "MA", 42.1015, -72.5898),
    ("Lansing", "MI", 42.7325, -84.5555),
    ("Detroit", "MI", 42.3314, -83.0458),
    ("Grand Rapids", "MI", 42.9634, -85.6681),
    ("Flint", "MI", 43.0125, -83.6875),
    ("Sikeston", "MO", 36.8767, -89.5878),
    ("Saint Paul", "MN", 44.9537, -93.0900),
    ("Minneapolis", "MN", 44.9778, -93.2650),
    ("Duluth", "MN", 46.7867, -92.1005),
    ("Rochester", "MN", 44.0121, -92.4802),
    ("Jackson", "MS", 32.2988, -90.1848),
    ("Gulfport", "MS", 30.3674, -89.0928),
    ("Hattiesburg", "MS", 31.3271, -89.2903),
    ("Jefferson City", "MO", 38.5767, -92.1735),
    ("St. Louis", "MO", 38.6270, -90.1994),
    ("Kansas City", "MO", 39.0997, -94.5786),
    ("Springfield", "MO", 37.2090, -93.2923),
    ("Columbia", "MO", 38.9517, -92.3341),
    ("Helena", "MT", 46.5891, -112.0391),
    ("Billings", "MT", 45.7833, -108.5007),
    ("Missoula", "MT", 46.8721, -113.9940),
    ("Lincoln", "NE", 40.8136, -96.7026),
    ("Omaha", "NE", 41.2565, -95.9345),
    ("Grand Island", "NE", 40.9264, -98.3420),
    ("Carson City", "NV", 39.1638, -119.7674),
    ("Las Vegas", "NV", 36.1699, -115.1398),
    ("Reno", "NV", 39.5296, -119.8138),
    ("Concord", "NH", 43.2081, -71.5376),
    ("Manchester", "NH", 42.9956, -71.4548),
    ("Trenton", "NJ", 40.2171, -74.7429),
    ("Newark", "NJ", 40.7357, -74.1724),
    ("Camden", "NJ", 39.9259, -75.1196),
    ("Santa Fe", "NM", 35.6870, -105.9378),
    ("Albuquerque", "NM", 35.0844, -106.6504),
    ("Las Cruces", "NM", 32.3199, -106.7637),
    ("Albany", "NY", 42.6526, -73.7562),
    ("New York", "NY", 40.7128, -74.0060),
    ("Buffalo", "NY", 42.8864, -78.8784),
    ("Rochester", "NY", 43.1566, -77.6088),
    ("Syracuse", "NY", 43.0481, -76.1474),
    ("Raleigh", "NC", 35.7796, -78.6382),
    ("Charlotte", "NC", 35.2271, -80.8431),
    ("Greensboro", "NC", 36.0726, -79.7920),
    ("Asheville", "NC", 35.5951, -82.5515),
    ("Bismarck", "ND", 46.8083, -100.7837),
    ("Fargo", "ND", 46.8772, -96.7898),
    ("Columbus", "OH", 39.9612, -82.9988),
    ("Cleveland", "OH", 41.4993, -81.6944),
    ("Cincinnati", "OH", 39.1031, -84.5120),
    ("Toledo", "OH", 41.6528, -83.5379),
    ("Dayton", "OH", 39.7589, -84.1916),
    ("Oklahoma City", "OK", 35.4676, -97.5164),
    ("Tulsa", "OK", 36.1540, -95.9928),
    ("Salem", "OR", 44.9429, -123.0351),
    ("Portland", "OR", 45.5152, -122.6784),
    ("Eugene", "OR", 44.0521, -123.0868),
    ("Bend", "OR", 44.0582, -121.3153),
    ("Harrisburg", "PA", 40.2732, -76.8867),
    ("Philadelphia", "PA", 39.9526, -75.1652),
    ("Pittsburgh", "PA", 40.4406, -79.9959),
    ("Erie", "PA", 42.1292, -80.0851),
    ("Providence", "RI", 41.8240, -71.4128),
    ("Columbia", "SC", 34.0007, -81.0348),
    ("Charleston", "SC", 32.7765, -79.9311),
    ("Greenville", "SC", 34.8526, -82.3940),
    ("Pierre", "SD", 44.3683, -100.3510),
    ("Sioux Falls", "SD", 43.5460, -96.7313),
    ("Rapid City", "SD", 44.0805, -103.2310),
    ("Nashville", "TN", 36.1627, -86.7816),
    ("Memphis", "TN", 35.1495, -90.0490),
    ("Knoxville", "TN", 35.9606, -83.9207),
    ("Chattanooga", "TN", 35.0456, -85.3097),
    ("Austin", "TX", 30.2672, -97.7431),
    ("Houston", "TX", 29.7604, -95.3698),
    ("Dallas", "TX", 32.7767, -96.7970),
    ("San Antonio", "TX", 29.4241, -98.4936),
    ("El Paso", "TX", 31.7619, -106.4850),
    ("Amarillo", "TX", 35.2220, -101.8313),
    ("Lubbock", "TX", 33.5779, -101.8552),
    ("Abilene", "TX", 32.4487, -99.7331),
    ("Salt Lake City", "UT", 40.7608, -111.8910),
    ("Provo", "UT", 40.2338, -111.6585),
    ("Ogden", "UT", 41.2230, -111.9738),
    ("Montpelier", "VT", 44.2601, -72.5754),
    ("Burlington", "VT", 44.4759, -73.2121),
    ("Richmond", "VA", 37.5407, -77.4360),
    ("Virginia Beach", "VA", 36.8529, -75.9780),
    ("Roanoke", "VA", 37.2710, -79.9414),
    ("Norfolk", "VA", 36.8508, -76.2859),
    ("Olympia", "WA", 47.0379, -122.9007),
    ("Seattle", "WA", 47.6062, -122.3321),
    ("Spokane", "WA", 47.6588, -117.4260),
    ("Yakima", "WA", 46.6021, -120.5059),
    ("Charleston", "WV", 38.3498, -81.6326),
    ("Huntington", "WV", 38.4192, -82.4452),
    ("Madison", "WI", 43.0731, -89.4012),
    ("Milwaukee", "WI", 43.0389, -87.9065),
    ("Green Bay", "WI", 44.5133, -88.0133),
    ("La Crosse", "WI", 43.8014, -91.2396),
    ("Cheyenne", "WY", 41.1400, -104.8202),
    ("Casper", "WY", 42.8501, -106.3252),
]

# The GeoNames extract's tab-separated column indices we need (0-based, per the documented format).
_GEONAMES_NAME = 1
_GEONAMES_LAT = 4
_GEONAMES_LNG = 5
_GEONAMES_FEATURE_CLASS = 6
_GEONAMES_COUNTRY = 8
_GEONAMES_ADMIN1 = 10


def _from_geonames_extract(source: Path) -> list[tuple[str, str, float, float]]:
    rows: list[tuple[str, str, float, float]] = []
    seen: set[tuple[str, str]] = set()
    with source.open(encoding="utf-8") as f:
        for line in f:
            cols = line.rstrip("\n").split("\t")
            if len(cols) <= _GEONAMES_ADMIN1:
                continue
            if cols[_GEONAMES_COUNTRY] != "US" or cols[_GEONAMES_FEATURE_CLASS] != "P":
                continue
            name = cols[_GEONAMES_NAME].strip()
            state = cols[_GEONAMES_ADMIN1].strip()
            key = (name, state)
            if not name or not state or key in seen:
                continue
            seen.add(key)
            rows.append((name, state, float(cols[_GEONAMES_LAT]), float(cols[_GEONAMES_LNG])))
    rows.sort()
    return rows


def build(source: Path | None) -> list[tuple[str, str, float, float]]:
    return _from_geonames_extract(source) if source else sorted(SEED_PLACES)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path, default=None, help="a raw GeoNames extract (tab-separated)"
    )
    parser.add_argument("--out", type=Path, default=OUTPUT_PATH, help="output CSV path")
    args = parser.parse_args()

    if args.source is not None and not args.source.exists():
        print(f"error: --source {args.source} does not exist", file=sys.stderr)
        raise SystemExit(1)

    rows = build(args.source)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "state", "lat", "lng"])
        writer.writerows(rows)

    mode = "GeoNames extract" if args.source else "curated seed list (no --source given)"
    print(f"wrote {len(rows)} places to {args.out} (from {mode})")


if __name__ == "__main__":
    main()
