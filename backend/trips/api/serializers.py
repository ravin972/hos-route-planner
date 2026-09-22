"""Request validation (architecture.md section 6.1). Response shapes are documented for OpenAPI
by ``schema.py``, but the actual response body is the plain dict ``services.plan_trip`` already
builds to the documented contract -- re-running it through an output serializer would just
duplicate that shaping work for no correctness benefit (services.py is the single source of truth
for the response shape, matching AD-2's "one implementation" principle applied to the API layer).
"""

from typing import Any

from rest_framework import serializers


class StrictSerializer(serializers.Serializer[Any]):
    """architecture.md section 6.2's rule: "unknown request fields rejected". DRF ignores unknown
    keys by default; this rejects them explicitly, once, for every serializer in this module.

    ``Serializer[Any]``: DRF's stubs make ``Serializer`` generic over the model/object instance a
    serializer round-trips to (``BaseSerializer[_IN]``) -- these serializers validate a plain
    request body with no backing instance, so ``Any`` is the correct, idiomatic argument, not a
    workaround.
    """

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            unknown = set(data.keys()) - set(self.fields.keys())
            if unknown:
                raise serializers.ValidationError(
                    {name: "unknown field" for name in sorted(unknown)}
                )
        return super().to_internal_value(data)  # type: ignore[no-any-return]


class LocationInputSerializer(StrictSerializer):
    """Exactly one of ``{lat, lng}`` or ``query`` (architecture.md section 6.1)."""

    # "label" is also rest_framework.fields.Field's own display-label constructor argument; naming
    # this field to match the documented API contract (architecture.md section 6.1's
    # {"label"?: string, "lat", "lng"}) means shadowing it, which DRF's own field-collection
    # metaclass handles correctly at runtime (it works purely by class-attribute name) but a type
    # checker cannot verify structurally -- hence the one narrow, explained ignore below, not a
    # blanket suppression of unrelated DRF typing issues.
    label = serializers.CharField(required=False, allow_blank=True, max_length=200)  # type: ignore[assignment]
    lat = serializers.FloatField(required=False)
    lng = serializers.FloatField(required=False)
    query = serializers.CharField(required=False, allow_blank=False, max_length=200)

    def validate(self, attrs: Any) -> Any:
        has_coords = "lat" in attrs or "lng" in attrs
        has_query = "query" in attrs
        if has_coords and "lat" not in attrs:
            raise serializers.ValidationError({"lat": "lat is required when lng is given"})
        if has_coords and "lng" not in attrs:
            raise serializers.ValidationError({"lng": "lng is required when lat is given"})
        if has_coords == has_query:
            raise serializers.ValidationError(
                "provide exactly one of {lat, lng} or query, not both and not neither"
            )
        return attrs


class PlanRequestSerializer(StrictSerializer):
    """``POST /api/trips/plan`` -- architecture.md section 6.1. No ``departure_at`` field: there
    is no user-configurable departure time anywhere in this API (Q4, hos-rules.md A-16)."""

    current_location = LocationInputSerializer()
    pickup_location = LocationInputSerializer()
    dropoff_location = LocationInputSerializer()
    cycle_used_hours = serializers.FloatField(min_value=0, max_value=70)


class LocationSearchQuerySerializer(StrictSerializer):
    """``GET /api/locations/search?q=&limit=`` (architecture.md section 6, AD-6: US only)."""

    q = serializers.CharField(required=True, allow_blank=False, max_length=200)
    limit = serializers.IntegerField(required=False, default=5, min_value=1, max_value=20)
