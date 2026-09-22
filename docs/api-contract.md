# API contract

> Written in Phase 3, as scheduled by `architecture.md` section 6 ("The detailed field-by-field
> contract will be written to `docs/api-contract.md` in Phase 3"). This documents what the running
> code actually returns (`trips/services.py`), not an aspirational shape -- every field here is
> produced by a specific line of code, and `trips/tests/api/` and `trips/tests/test_services.py`
> check it. The machine-readable version is `GET /api/schema/`; a browsable UI is `GET /api/docs/`.

Base path `/api`. JSON in and out. No authentication (AD-1). CORS allow-list
(`CORS_ALLOWED_ORIGINS`). Distances are miles. Timestamps are ISO-8601 with a fixed offset for the
whole trip (AD-11). Grid positions are integer minute-of-local-day (0-1440).

## Endpoints

| Method - path | Purpose |
| --- | --- |
| `GET /api/health` | liveness |
| `GET /api/locations/search?q=&limit=` | typeahead (US only) |
| `POST /api/trips/plan` | the product |
| `GET /api/schema/` | OpenAPI 3 schema (JSON) |
| `GET /api/docs/` | Swagger UI |

## Errors (architecture.md section 4.4)

One envelope everywhere: `{"error": {"code": string, "message": string, "fields"?: object}}`.

| HTTP | `code` | When |
| --- | --- | --- |
| 400 | `validation_error` | bad/missing/unknown field, `cycle_used_hours` outside 0-70, a location outside the contiguous US bounds |
| 422 | `unroutable` | no drivable route between the given points |
| 422 | `out_of_coverage` | the route exceeds the provider's own limits (> 6,000 km) or a point is not road-connected |
| 429 | `throttled` | rate limit exceeded (`THROTTLE_PLAN` / `THROTTLE_SEARCH`, per IP) |
| 502 | `upstream_error` | ORS/Photon returned 5xx, a malformed response, or is not configured (for example, no `ORS_API_KEY` -- see the Phase 2 risk R-ORS-LIVE) |
| 504 | `upstream_timeout` | the provider did not respond within the configured timeout, even after one retry |
| 500 | `plan_self_check_failed` | the independent validator found a violation in a plan the planner produced -- a bug, logged at ERROR, never returned to the client |

`cycle_exhausted` is **not** an error: a trip that needs more of the 70-hour cycle than the driver
has left is HTTP 200 with `summary.status = "cycle_exhausted"` (AD-14).

## `GET /api/health`

```jsonc
200 { "status": "ok", "version": "0.1.0" }
```

## `GET /api/locations/search?q=&limit=`

Query params: `q` (required, 1-200 chars), `limit` (optional, 1-20, default 5).

```jsonc
200 { "results": [ { "label": "Chicago, Illinois", "lat": 41.8756, "lng": -87.6244 } ] }
```

US results only (`countrycode == "US"`, AD-6); non-US results are silently dropped, not an error.

## `POST /api/trips/plan`

### Request

```jsonc
{
  "current_location": { "label"?: string, "lat": number, "lng": number },   // or { "query": string }
  "pickup_location":  { /* same shape */ },
  "dropoff_location": { /* same shape */ },
  "cycle_used_hours": number   // 0-70, decimals ok
}
```

- Each location is **exactly one of** `{lat, lng}` (optionally with `label`) or `{query}` -- never
  both, never neither. A `query` location is resolved via `GET /api/locations/search`'s same
  geocoder, taking the top hit.
- **No `departure_at` field exists.** Departure is a fixed convention -- 08:00 local time on
  today's date in the origin's time zone -- never a request input (Q4, hos-rules.md A-16).
- Unknown top-level or per-location fields are rejected (400).
- `current_location`, `pickup_location` and `dropoff_location` must each resolve to a point inside
  the contiguous US (a simple latitude/longitude bounding box -- see "Known limitations" below).

### Response (`200`, `TripPlan`)

```jsonc
{
  "summary": {
    "status": "complete",                    // or "cycle_exhausted" -- still HTTP 200 (AD-14)
    "route_distance_mi": 850.0,               // the provider's routed distance
    "planned_distance_mi": 850.0,             // miles actually driven; < route_distance_mi only when cycle_exhausted
    "total_driving_hours": 15.47,
    "total_on_duty_hours": 17.97,
    "departure_at": "2026-09-22T08:00:00-05:00",
    "arrival_at": "2026-09-23T11:58:00-05:00",  // null when cycle_exhausted
    "days": 2,
    "timezone": "America/Chicago",            // the origin's IANA zone
    "utc_offset": "-05:00",                   // one fixed offset for the whole trip (AD-11)
    "stop_counts": { "fuel": 0, "break": 0, "rest": 1, "restart": 0 },
    "cycle": {
      "used_at_start_h": 0.0, "used_at_end_h": 17.97,
      "remaining_h": 52.03, "limit_h": 70.0,
      "status": "ok"                          // "exhausted" when the allowance ran out
    },
    "unplanned": null   // when cycle_exhausted: { "miles", "pending": ["dropoff", ...], "blocked", "shortfall_h" }
  },
  "assumptions": {
    "avg_speed_mph": 55.0, "pickup_min": 60, "dropoff_min": 60, "pretrip_min": 15,
    "fuel_stop_min": 30, "fuel_interval_mi": 1000.0, "cycle_limit_h": 70.0,
    "restart_applied": false,                 // always false: not reachable via this API (D-2)
    "departure_local_time": "08:00"
  },
  "route": {
    "geometry": "<encoded polyline, precision 5, simplified to <= 5000 points>",
    "bounds": [[minLat, minLng], [maxLat, maxLng]],
    "legs": [
      { "kind": "to_pickup", "from": {"label","lat","lng"}, "to": {"label","lat","lng"},
        "distance_mi": 300.0, "steps": [ {"instruction","distance_mi","road"} ] },
      { "kind": "to_dropoff", "...": "..." }
    ]
  },
  "stops": [
    { "id": "s0", "type": "start", "reason": "trip_start", "label": "Chicago, IL",
      "lat": 41.8781, "lng": -87.6298, "route_mile": 0.0,
      "arrive_at": "...", "depart_at": "...", "duration_min": 0, "duty_status": "OFF" }
    // type in {start, pretrip, pickup, fuel, break, rest, dropoff, cycle_limit, restart}
    // (restart never appears via this API -- the internal option is always off, D-2)
    // ids are sequential (s0, s1, s2, ...); route_mile is non-decreasing
  ],
  "daily_logs": [
    { "date": "2026-09-22", "day_number": 1, "from": "Chicago, IL", "to": "...",
      "miles_driven": 604.3,
      "header": { "carrier": "", "main_office": "", "home_terminal": "", "vehicle": "" },
      "totals_h": { "OFF": 8.0, "SB": 3.75, "D": 11.0, "ON": 1.25 },   // sums to exactly 24.0
      "segments": [ { "status": "OFF", "start_min": 0, "end_min": 480, "kind": "idle" } ],  // 0..1440, contiguous
      "remarks":  [ { "minute": 480, "place": "Chicago, IL", "note": "Pre-trip inspection" } ],
      "recap":    { "on_duty_today_h": 12.25, "a_last_8_days_h": 12.25,
                    "b_available_tomorrow_h": 57.75, "c_last_5_days_h": null },  // Q7 still open; C stays null
      "summary":  { "driving_h": 11.0, "on_duty_h": 12.25, "off_duty_h": 8.0, "sleeper_h": 3.75,
                    "miles": 604.3, "stop_ids": ["s0","s1","s2","s3"], "cycle_remaining_h": 57.75 } }
  ],
  "warnings": [    // always present; empty unless summary.status == "cycle_exhausted"
    { "code": "cycle_exhausted", "severity": "violation",
      "message": "The 70-hour cycle runs out at mile 437.5 (Day 1, 16:00). 412.5 mi and the drop-off remain; at least 9.25 more on-duty hours are needed. No 34-hour restart applied.",
      "details": { "stopped_at_mile": 437.5, "blocked": "drive", "pending": ["dropoff"],
                    "unplanned_miles": 412.5, "shortfall_min": 555 } }
  ]
}
```

**Invariants (checked by `trips/tests/test_services.py` and `trips/tests/api/test_plan.py`):**
every `daily_logs[i].segments` sums to exactly 1,440 minutes; `stops[].route_mile` is
non-decreasing; `warnings` is always an array (possibly empty); a `cycle_exhausted` response's
`daily_logs` ends at the stop, `summary.arrival_at` is `null`, and the underlying timeline still
passes the independent validator (AD-14) -- `services.py` raises `plan_self_check_failed` (500)
rather than ever return a plan it can't verify.

## Known limitations (disclosed, not silent)

- **"Contiguous US" is a rectangular latitude/longitude bounding box**
  (`trips/services.py::CONUS_BOUNDS`), not a precise border polygon. It correctly excludes Alaska,
  Hawaii and points far outside the US, but a simple rectangle necessarily includes some non-US
  territory near the northern border (for example, southern Ontario) -- the docs don't specify a
  more precise algorithm, and a real border polygon was judged out of scope for this assessment.
- **The offline place-name lookup (`trips/routing/places.py`) uses a curated ~180-place seed list**,
  not a full GeoNames import -- this environment has no network access to GeoNames' download
  server. `scripts/build_places.py --source <geonames-extract>` regenerates the CSV from a real
  extract when one is available; a point more than 50 miles from every seed place falls back to a
  `"near {lat}, {lng}"` label rather than a wrong city name (AD-13: never silently wrong).
- **`restart_applied` is always `false`** and no `restart`-typed stop can appear through this API --
  the internal 34-hour-restart option is not reachable from any request (D-2).
