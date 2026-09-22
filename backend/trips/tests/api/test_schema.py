"""OpenAPI schema generation and the Swagger UI page (architecture.md AD-12, section 6)."""

from rest_framework.test import APIClient


def test_schema_generates_without_error() -> None:
    """drf-spectacular walks every registered view to build the schema; this fails loudly if any
    view is mis-annotated (e.g. a bad @extend_schema) rather than only at deploy time."""
    from drf_spectacular.generators import SchemaGenerator

    schema = SchemaGenerator().get_schema(request=None, public=True)
    assert schema["info"]["title"] == "Spotter HOS Planner API"
    paths = schema["paths"]
    assert "/api/health" in paths
    assert "/api/trips/plan" in paths
    assert "/api/locations/search" in paths
    assert "post" in paths["/api/trips/plan"]
    assert "get" in paths["/api/locations/search"]


def test_schema_endpoint_returns_200() -> None:
    response = APIClient().get("/api/schema/")
    assert response.status_code == 200
    assert "openapi" in response.content.decode()


def test_docs_endpoint_returns_200() -> None:
    """The Swagger UI page (architecture.md section 6: GET /api/docs/) -- needs Django's template
    engine configured to find drf-spectacular's bundled template; regression-tests that config."""
    response = APIClient().get("/api/docs/")
    assert response.status_code == 200
    assert b"swagger" in response.content.lower()
