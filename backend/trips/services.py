"""``plan_trip()``: the orchestrator (architecture.md section 4.2) -- the only place in this
codebase that imports both ``trips.hos`` and ``trips.routing``. It composes inputs and outputs; it
never recomputes anything ``trips.hos`` already decided. Every number in the response that looks
like a schedule fact (a time, a duty status, a total) traces back to a ``hos.plan()`` /
``hos.validate()`` call a few lines below -- this file only resolves locations, calls the HOS
engine once, and reshapes its answer plus the routing provider's answer into the documented JSON
contract (architecture.md section 6.2).
"""

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import timezone as dt_timezone
from zoneinfo import ZoneInfo

from trips.hos import constants as hos_constants
from trips.hos.logs import build_daily_logs
from trips.hos.planner import plan as hos_plan
from trips.hos.types import CycleStop, DailyLog, Kind, PlanParams, PlanResult, PlanStatus, Status
from trips.hos.validator import validate as hos_validate
from trips.routing.base import GeocodingService, Place, Route, RoutingService
from trips.routing.geometry import MileIndex, decode_polyline, encode_polyline, simplify
from trips.routing.places import nearest_place_label
from trips.routing.timezone import iana_zone_for, utc_offset_at

# --- inputs -----------------------------------------------------------------------------------

CONUS_BOUNDS = {"min_lat": 24.396308, "max_lat": 49.384358, "min_lng": -125.0, "max_lng": -66.93457}
DEPARTURE_LOCAL_TIME = "08:00"  # A-16: fixed, not user-configurable
DEPARTURE_MINUTE = 8 * 60  # this trip's own minute-0 day always starts here (A-16)


class TripInputError(ValueError):
    """A request-shaped problem services.py itself catches (not a provider failure). The API
    layer maps this to HTTP 400 ``validation_error`` (architecture.md section 4.4)."""


class PlanSelfCheckFailedError(Exception):
    """The independent validator found a violation in a plan the planner produced. A bug, not a
    user error -- architecture.md AD-13/section 4.4: HTTP 500 ``plan_self_check_failed``, logged
    at ERROR. Carries the violations so the caller can log them."""

    def __init__(self, violations: Sequence[object]) -> None:
        super().__init__(f"{len(violations)} violation(s) in a plan the planner produced")
        self.violations = violations


@dataclass(frozen=True)
class LocationInput:
    """Exactly one of (lat, lng) or query must be set -- enforced by the request serializer, not
    re-checked here (services.py trusts its caller's already-validated input, matching AD-2's
    "frozen dataclasses in" boundary discipline)."""

    label: str | None
    lat: float | None
    lng: float | None
    query: str | None


@dataclass(frozen=True)
class TripPlanInputs:
    current_location: LocationInput
    pickup_location: LocationInput
    dropoff_location: LocationInput
    cycle_used_hours: float


# --- orchestration ------------------------------------------------------------------------------


def plan_trip(
    inputs: TripPlanInputs,
    *,
    routing: Callable[[], RoutingService],
    geocoding: GeocodingService,
    params: PlanParams | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    """architecture.md section 4.2, steps 1-8. ``now`` is injectable for deterministic tests --
    the planner itself has no clock (hos-rules.md section 8: "the planner has no clock, no I/O, no
    randomness"); this is the one place "now" is ever resolved, exactly as that rule requires.

    ``routing`` is a zero-argument factory, not an already-constructed adapter: steps 1-2 below
    (location resolution, CONUS bounds, cycle range) need only ``geocoding`` and must be able to
    raise their own ``TripInputError`` -- HTTP 400 -- independently of whether the routing provider
    is even reachable. Building the adapter eagerly, before those checks ran, previously let a
    provider failure (say, a missing ``ORS_API_KEY``) mask a genuinely invalid request behind a
    502 instead of the documented 400 (found in Phase 5 integration testing)."""
    if params is None:
        from django.conf import settings

        params = PlanParams(avg_speed_mph=getattr(settings, "AVG_TRUCK_SPEED_MPH", 55))

    # 1. resolve each location
    current = _resolve_location(inputs.current_location, geocoding)
    pickup = _resolve_location(inputs.pickup_location, geocoding)
    dropoff = _resolve_location(inputs.dropoff_location, geocoding)

    # 2. validate bounds; convert cycle_used_hours -> int minutes once (rule M-1, round half up)
    for place in (current, pickup, dropoff):
        _require_conus(place)
    if not (0 <= inputs.cycle_used_hours <= 70):
        raise TripInputError(f"cycle_used_hours must be in [0, 70], got {inputs.cycle_used_hours}")
    cycle_used_min = math.floor(inputs.cycle_used_hours * 60 + 0.5)

    # 3. only now construct the routing adapter and route the whole trip in one call
    route = routing().route(
        [(current.lat, current.lng), (pickup.lat, pickup.lng), (dropoff.lat, dropoff.lng)]
    )

    # 4. mile -> coordinate index, from the full-resolution geometry
    full_points = decode_polyline(route.geometry)
    mile_index = MileIndex(full_points, route.distance_mi) if len(full_points) >= 2 else None

    # 5. resolve the origin's time zone -> one fixed UTC offset; derive departure (A-16)
    zone_name = iana_zone_for(current.lat, current.lng)
    now = now or datetime.now(tz=UTC)
    today_local = now.astimezone(ZoneInfo(zone_name)).date()
    departure_naive = datetime.combine(today_local, datetime.min.time()) + timedelta(
        minutes=DEPARTURE_MINUTE
    )
    utc_offset = utc_offset_at(zone_name, departure_naive.replace(tzinfo=ZoneInfo(zone_name)))
    trip_tz = dt_timezone(utc_offset)

    def to_datetime(minute: int) -> datetime:
        """Absolute minute (this trip's own timeline) -> a real, fixed-offset instant. One offset
        for the whole trip (AD-11) -- never re-resolved per day, so a DST change mid-trip shifts
        wall-clock by an hour rather than the timestamps silently jumping (documented)."""
        return datetime.combine(today_local, datetime.min.time(), tzinfo=trip_tz) + timedelta(
            minutes=minute
        )

    leg1_mi = route.legs[0].distance_mi
    leg2_mi = route.legs[1].distance_mi

    # 6. the HOS engine -- the only authority on the schedule
    result = hos_plan(leg1_mi, leg2_mi, cycle_used_min, DEPARTURE_MINUTE, params)
    daily_logs = build_daily_logs(result)
    violations = hos_validate(
        result.segments, cycle_used_min, params, DEPARTURE_MINUTE, daily_logs=daily_logs
    )
    if violations:
        raise PlanSelfCheckFailedError(violations)

    # 7-8. assemble the response
    return _assemble_response(
        result=result,
        daily_logs=daily_logs,
        route=route,
        mile_index=mile_index,
        current=current,
        pickup=pickup,
        dropoff=dropoff,
        cycle_used_hours_in=inputs.cycle_used_hours,
        params=params,
        zone_name=zone_name,
        utc_offset=utc_offset,
        to_datetime=to_datetime,
    )


def _resolve_location(loc: LocationInput, geocoding: GeocodingService) -> Place:
    if loc.lat is not None and loc.lng is not None:
        return Place(label=loc.label or f"{loc.lat:.4f}, {loc.lng:.4f}", lat=loc.lat, lng=loc.lng)
    if loc.query:
        hits = geocoding.search(loc.query, limit=1)
        if not hits:
            raise TripInputError(f"no US location found for {loc.query!r}")
        return hits[0]
    raise TripInputError("a location needs either {lat, lng} or {query}")


def _require_conus(place: Place) -> None:
    b = CONUS_BOUNDS
    if not (
        b["min_lat"] <= place.lat <= b["max_lat"] and b["min_lng"] <= place.lng <= b["max_lng"]
    ):
        raise TripInputError(
            f"{place.label} ({place.lat}, {place.lng}) is outside the contiguous US"
        )


# --- response assembly (architecture.md section 6.2) --------------------------------------------

_STOP_META: dict[Kind, tuple[str, str, str]] = {
    # Kind -> (type, reason, duty_status)
    Kind.PRETRIP: ("pretrip", "pretrip_inspection", "ON"),
    Kind.PICKUP: ("pickup", "pickup", "ON"),
    Kind.FUEL: ("fuel", "fuel_1000mi", "ON"),
    Kind.BREAK: ("break", "hos_break_30min", "OFF"),
    Kind.REST: ("rest", "hos_reset_10h", "SB"),
    Kind.DROPOFF: ("dropoff", "dropoff", "ON"),
    Kind.RESTART: ("restart", "restart_34h", "OFF"),  # never reachable via the API (D-2)
}


def _place_dict(place: Place) -> dict[str, object]:
    return {"label": place.label, "lat": place.lat, "lng": place.lng}


def _format_offset(offset: timedelta) -> str:
    total_min = int(offset.total_seconds() // 60)
    sign = "+" if total_min >= 0 else "-"
    total_min = abs(total_min)
    return f"{sign}{total_min // 60:02d}:{total_min % 60:02d}"


def _log_header() -> dict[str, str]:
    from django.conf import settings

    return {
        "carrier": getattr(settings, "LOG_CARRIER_NAME", "") or "",
        "main_office": getattr(settings, "LOG_MAIN_OFFICE", "") or "",
        "home_terminal": getattr(settings, "LOG_HOME_TERMINAL", "") or "",
        "vehicle": getattr(settings, "LOG_TRUCK_NUMBER", "") or "",
    }


def _exhausted_warning_message(stop: CycleStop, day_number: int, hm: str) -> str:
    pending_words = {Kind.PICKUP: "the pickup", Kind.DROPOFF: "the drop-off"}
    pending_desc = " and ".join(pending_words[k] for k in stop.pending)
    return (
        f"The 70-hour cycle runs out at mile {stop.mile:.1f} (Day {day_number}, {hm}). "
        f"{stop.unplanned_miles:.1f} mi and {pending_desc} remain; at least "
        f"{stop.shortfall_min / 60:.2f} more on-duty hours are needed. No 34-hour restart applied."
    )


def _assemble_response(
    *,
    result: PlanResult,
    daily_logs: list[DailyLog],
    route: Route,
    mile_index: MileIndex | None,
    current: Place,
    pickup: Place,
    dropoff: Place,
    cycle_used_hours_in: float,
    params: PlanParams,
    zone_name: str,
    utc_offset: timedelta,
    to_datetime: Callable[[int], datetime],
) -> dict[str, object]:
    def coords_at(mile: float) -> tuple[float, float]:
        if mile_index is not None:
            return mile_index.at(mile)
        return (current.lat, current.lng)

    def label_at(mile: float) -> str:
        lat, lng = coords_at(mile)
        return nearest_place_label(lat, lng)

    # --- stops --- (stop_minutes tracks each stop's absolute trip-timeline minute alongside its
    # id, purely so the daily-log loop below can bucket stops by day without re-parsing a
    # rendered ISO timestamp back into a minute)
    stop_minutes: dict[str, int] = {"s0": result.departure}
    stops: list[dict[str, object]] = [
        {
            "id": "s0",
            "type": "start",
            "reason": "trip_start",
            "label": current.label,
            "lat": current.lat,
            "lng": current.lng,
            "route_mile": 0.0,
            "arrive_at": to_datetime(result.departure).isoformat(),
            "depart_at": to_datetime(result.departure).isoformat(),
            "duration_min": 0,
            "duty_status": "OFF",
        }
    ]
    for seg in result.segments:
        meta = _STOP_META.get(seg.kind)
        if meta is None:  # DRIVE, IDLE: not a stop
            continue
        stop_type, reason, duty_status = meta
        # pickup/dropoff coordinates are already known exactly (they were geocoded); every other
        # stop only has a route mile, so it must be interpolated along the mile index.
        if seg.kind == Kind.PICKUP:
            lat, lng, label = pickup.lat, pickup.lng, pickup.label
        elif seg.kind == Kind.DROPOFF:
            lat, lng, label = dropoff.lat, dropoff.lng, dropoff.label
        else:
            lat, lng = coords_at(seg.pos_start)
            label = nearest_place_label(lat, lng)
        stop_id = f"s{len(stops)}"
        stop_minutes[stop_id] = seg.start
        stops.append(
            {
                "id": stop_id,
                "type": stop_type,
                "reason": reason,
                "label": label,
                "lat": lat,
                "lng": lng,
                "route_mile": round(seg.pos_start, 1),
                "arrive_at": to_datetime(seg.start).isoformat(),
                "depart_at": to_datetime(seg.end).isoformat(),
                "duration_min": seg.minutes,
                "duty_status": duty_status,
            }
        )

    if result.status == PlanStatus.CYCLE_EXHAUSTED:
        stop = result.stop
        assert stop is not None
        lat, lng = coords_at(stop.mile)
        cycle_limit_id = f"s{len(stops)}"
        stop_minutes[cycle_limit_id] = stop.minute
        stops.append(
            {
                "id": cycle_limit_id,
                "type": "cycle_limit",
                "reason": "cycle_exhausted",
                "label": nearest_place_label(lat, lng),
                "lat": lat,
                "lng": lng,
                "route_mile": round(stop.mile, 1),
                "arrive_at": to_datetime(stop.minute).isoformat(),
                "depart_at": to_datetime(stop.minute).isoformat(),
                "duration_min": 0,
                "duty_status": "OFF",
            }
        )

    # --- route ---
    full_points = decode_polyline(route.geometry)
    display_points = simplify(full_points) if full_points else full_points

    # route.legs' own from_place/to_place carry no label (the adapter only knows coordinates);
    # the trip's own resolved endpoints are the only two named locations we actually know, so
    # they are used directly here rather than built once from the adapter's Place and patched
    # over afterwards.
    leg_endpoints = [(current, pickup), (pickup, dropoff)]
    legs_out: list[dict[str, object]] = []
    for i, leg in enumerate(route.legs):
        from_place, to_place = leg_endpoints[i] if i < len(leg_endpoints) else (current, dropoff)
        legs_out.append(
            {
                "kind": "to_pickup" if i == 0 else "to_dropoff",
                "from": _place_dict(from_place),
                "to": _place_dict(to_place),
                "distance_mi": leg.distance_mi,
                "steps": [
                    {"instruction": s.instruction, "distance_mi": s.distance_mi, "road": s.road}
                    for s in leg.steps
                ],
            }
        )
    route_out: dict[str, object] = {
        "geometry": encode_polyline(display_points) if display_points else route.geometry,
        "bounds": [list(route.bounds[0]), list(route.bounds[1])],
        "legs": legs_out,
    }

    # --- daily logs ---
    day0 = to_datetime(0).date()
    daily_logs_out = []
    for log in daily_logs:
        day_date = day0 + timedelta(days=log.day_index)
        totals_h = {
            "OFF": log.totals.off / 60,
            "SB": log.totals.sb / 60,
            "D": log.totals.d / 60,
            "ON": log.totals.on / 60,
        }
        day_start_min = log.day_index * hos_constants.MINUTES_PER_DAY
        day_end_min = day_start_min + hos_constants.MINUTES_PER_DAY
        stop_ids = [
            stop_id
            for stop_id, minute in stop_minutes.items()
            if day_start_min <= minute < day_end_min
        ]
        first_mi = log.segments[0].pos_start if log.segments else 0.0
        last_mi = log.segments[-1].pos_end if log.segments else 0.0
        daily_logs_out.append(
            {
                "date": day_date.isoformat(),
                "day_number": log.day_number,
                "from": label_at(first_mi),
                "to": label_at(last_mi),
                "miles_driven": log.miles,
                "header": _log_header(),
                "totals_h": totals_h,
                "segments": [
                    {
                        "status": s.status.value,
                        "start_min": s.start_min,
                        "end_min": s.end_min,
                        "kind": s.kind.value,
                    }
                    for s in log.segments
                ],
                "remarks": [
                    {"minute": r.minute, "place": label_at(r.mile), "note": r.note}
                    for r in log.remarks
                ],
                "recap": {
                    "on_duty_today_h": log.recap.on_duty_today_min / 60,
                    "a_last_8_days_h": log.recap.cycle_used_min / 60,
                    "b_available_tomorrow_h": log.recap.available_min / 60,
                    "c_last_5_days_h": log.recap.last_5_days_min,
                },
                "summary": {
                    "driving_h": totals_h["D"],
                    "on_duty_h": totals_h["D"] + totals_h["ON"],
                    "off_duty_h": totals_h["OFF"],
                    "sleeper_h": totals_h["SB"],
                    "miles": log.miles,
                    "stop_ids": stop_ids,
                    "cycle_remaining_h": log.recap.available_min / 60,
                },
            }
        )

    # --- summary ---
    driven_mi = sum(s.miles for s in result.segments if s.status == Status.D)
    driving_min = sum(s.minutes for s in result.segments if s.status == Status.D)
    on_duty_min = sum(s.minutes for s in result.segments if s.status in (Status.D, Status.ON))
    cycle_used_end_min = result.carry_in_min + on_duty_min

    stop_counts = {"fuel": 0, "break": 0, "rest": 0, "restart": 0}
    for seg in result.segments:
        if seg.kind == Kind.FUEL:
            stop_counts["fuel"] += 1
        elif seg.kind == Kind.BREAK:
            stop_counts["break"] += 1
        elif seg.kind == Kind.REST:
            stop_counts["rest"] += 1
        elif seg.kind == Kind.RESTART:
            stop_counts["restart"] += 1

    warnings: list[dict[str, object]] = []
    unplanned: dict[str, object] | None = None
    if result.status == PlanStatus.CYCLE_EXHAUSTED:
        stop = result.stop
        assert stop is not None
        unplanned = {
            "miles": stop.unplanned_miles,
            "pending": [k.value for k in stop.pending],
            "blocked": stop.blocked.value,
            "shortfall_h": stop.shortfall_min / 60,
        }
        stop_day_number = stop.minute // hos_constants.MINUTES_PER_DAY + 1
        hm = to_datetime(stop.minute).strftime("%H:%M")
        warnings.append(
            {
                "code": "cycle_exhausted",
                "severity": "violation",
                "message": _exhausted_warning_message(stop, stop_day_number, hm),
                "details": {
                    "stopped_at_mile": stop.mile,
                    "blocked": stop.blocked.value,
                    "pending": [k.value for k in stop.pending],
                    "unplanned_miles": stop.unplanned_miles,
                    "shortfall_min": stop.shortfall_min,
                },
            }
        )

    summary = {
        "status": result.status.value,
        "route_distance_mi": route.distance_mi,
        "planned_distance_mi": driven_mi,
        "total_driving_hours": driving_min / 60,
        "total_on_duty_hours": on_duty_min / 60,
        "departure_at": to_datetime(result.departure).isoformat(),
        "arrival_at": to_datetime(result.end).isoformat()
        if result.status == PlanStatus.COMPLETE
        else None,
        "days": len(daily_logs),
        "timezone": zone_name,
        "utc_offset": _format_offset(utc_offset),
        "stop_counts": stop_counts,
        "cycle": {
            "used_at_start_h": cycle_used_hours_in,
            "used_at_end_h": cycle_used_end_min / 60,
            "remaining_h": (hos_constants.CYCLE_LIMIT_MIN - cycle_used_end_min) / 60,
            "limit_h": hos_constants.CYCLE_LIMIT_MIN / 60,
            "status": "ok" if result.status == PlanStatus.COMPLETE else "exhausted",
        },
        "unplanned": unplanned,
    }

    assumptions = {
        "avg_speed_mph": params.avg_speed_mph,
        "pickup_min": params.pickup_min,
        "dropoff_min": params.dropoff_min,
        "pretrip_min": params.pretrip_min,
        "fuel_stop_min": params.fuel_stop_min,
        "fuel_interval_mi": params.fuel_interval_miles,
        "cycle_limit_h": hos_constants.CYCLE_LIMIT_MIN / 60,
        "restart_applied": params.allow_34_hour_restart,
        "departure_local_time": DEPARTURE_LOCAL_TIME,
    }

    return {
        "summary": summary,
        "assumptions": assumptions,
        "route": route_out,
        "stops": stops,
        "daily_logs": daily_logs_out,
        "warnings": warnings,
    }
