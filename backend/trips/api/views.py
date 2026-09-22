"""HTTP verbs only -- every view calls straight into ``services.py`` and does nothing else
(architecture.md section 4.1: "api calls only services"). No view here contains a schedule
decision, a distance calculation, or a duty-status rule.
"""

from typing import Any

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from trips import __version__
from trips.routing.base import UpstreamError
from trips.routing.ors import OpenRouteServiceAdapter
from trips.routing.ors import from_env as ors_from_env
from trips.routing.photon import PhotonAdapter
from trips.routing.photon import from_env as photon_from_env
from trips.services import LocationInput, TripPlanInputs, plan_trip

from .serializers import LocationSearchQuerySerializer, PlanRequestSerializer
from .throttles import PlanRateThrottle, SearchRateThrottle


def _ors_adapter() -> OpenRouteServiceAdapter:
    """``from_env()`` raises a plain ``RuntimeError`` when ``ORS_API_KEY`` is unset -- a real
    server misconfiguration, but from the *caller's* point of view indistinguishable from "the
    routing provider is unavailable". Re-raised as the same typed error a live 5xx/timeout would
    produce, so every failure mode here returns the one JSON envelope, never a raw HTML
    traceback (architecture.md section 4.4)."""
    try:
        return ors_from_env()
    except RuntimeError as exc:
        raise UpstreamError(f"routing is not available: {exc}") from exc


def _photon_adapter() -> PhotonAdapter:
    return photon_from_env()


class HealthView(APIView):
    """Liveness probe. Touches no database and no external service."""

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT, description="{status: 'ok', version: string}"
            )
        }
    )
    def get(self, request: Request) -> Response:
        return Response({"status": "ok", "version": __version__})


def _location_input(data: dict[str, Any]) -> LocationInput:
    return LocationInput(
        label=data.get("label"), lat=data.get("lat"), lng=data.get("lng"), query=data.get("query")
    )


class PlanView(APIView):
    """``POST /api/trips/plan`` (architecture.md section 6.1) -- the product."""

    throttle_classes = [PlanRateThrottle]

    @extend_schema(
        request=PlanRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT, description="TripPlan -- see docs/api-contract.md"
            )
        },
        description=(
            "Plans a trip against the current HOS rules. A cycle_exhausted trip is still HTTP 200 "
            "(architecture.md AD-14) -- see summary.status, warnings and unplanned."
        ),
    )
    def post(self, request: Request) -> Response:
        serializer = PlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        inputs = TripPlanInputs(
            current_location=_location_input(data["current_location"]),
            pickup_location=_location_input(data["pickup_location"]),
            dropoff_location=_location_input(data["dropoff_location"]),
            cycle_used_hours=data["cycle_used_hours"],
        )
        result = plan_trip(inputs, routing=_ors_adapter, geocoding=_photon_adapter())
        return Response(result, status=200)


class LocationSearchView(APIView):
    """``GET /api/locations/search?q=&limit=`` (architecture.md AD-6) -- typeahead, US only."""

    throttle_classes = [SearchRateThrottle]

    @extend_schema(
        parameters=[LocationSearchQuerySerializer],
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT, description="{results: LocationSuggestion[]}"
            )
        },
    )
    def get(self, request: Request) -> Response:
        serializer = LocationSearchQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        places = _photon_adapter().search(data["q"], limit=data["limit"])
        results = [{"label": p.label, "lat": p.lat, "lng": p.lng} for p in places]
        return Response({"results": results}, status=200)
