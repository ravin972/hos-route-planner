"""The typed error envelope (architecture.md section 4.4): ``{"error": {"code", "message",
"fields"?}}`` everywhere, for every kind of failure this API can produce.
"""

import logging
from typing import Any

from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

from trips.routing.base import (
    OutOfCoverageError,
    UnroutableError,
    UpstreamError,
    UpstreamTimeoutError,
)
from trips.services import PlanSelfCheckFailedError, TripInputError

logger = logging.getLogger(__name__)

_STATUS_CODES = {
    "validation_error": 400,
    "unroutable": 422,
    "out_of_coverage": 422,
    "throttled": 429,
    "upstream_error": 502,
    "upstream_timeout": 504,
    "plan_self_check_failed": 500,
}


def _envelope(code: str, message: str, *, fields: dict[str, Any] | None = None) -> Response:
    body: dict[str, object] = {"code": code, "message": message}
    if fields:
        body["fields"] = fields
    return Response({"error": body}, status=_STATUS_CODES[code])


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Registered as ``REST_FRAMEWORK["EXCEPTION_HANDLER"]``. Typed errors from ``services.py`` and
    ``trips.routing`` are mapped explicitly first; everything DRF itself recognises (validation,
    throttling, 404/405) is reshaped into the same envelope; anything neither of those catches is
    left to Django's own error handling (never silently swallowed -- AD-13)."""

    if isinstance(exc, TripInputError):
        return _envelope("validation_error", str(exc))
    if isinstance(exc, UnroutableError):
        return _envelope("unroutable", exc.message)
    if isinstance(exc, OutOfCoverageError):
        return _envelope("out_of_coverage", exc.message)
    if isinstance(exc, UpstreamTimeoutError):
        return _envelope("upstream_timeout", exc.message)
    if isinstance(exc, UpstreamError):
        return _envelope("upstream_error", exc.message)
    if isinstance(exc, PlanSelfCheckFailedError):
        logger.error("plan_self_check_failed: %s", exc.violations)
        return _envelope("plan_self_check_failed", "the generated plan failed its own safety check")

    response = drf_default_handler(exc, context)
    if response is None:
        return None  # not a DRF-recognised exception either; let it surface as a real 500

    if isinstance(exc, drf_exceptions.Throttled):
        return _envelope("throttled", str(exc.detail))
    if isinstance(exc, drf_exceptions.ValidationError):
        fields = response.data if isinstance(response.data, dict) else None
        return _envelope("validation_error", "request validation failed", fields=fields)

    # any other DRF-recognised exception (404 NotFound, 405 MethodNotAllowed, ...): same envelope
    # shape, generic code -- not one of the architecture.md section 4.4 table's named codes, since
    # those cover /api/trips/plan and /api/locations/search specifically, not routing mismatches.
    detail = exc.detail if hasattr(exc, "detail") else str(exc)
    return Response(
        {"error": {"code": "error", "message": str(detail)}}, status=response.status_code
    )
