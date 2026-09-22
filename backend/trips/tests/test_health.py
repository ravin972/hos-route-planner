from rest_framework.test import APIClient

from trips import __version__


def test_health_reports_ok_and_the_app_version() -> None:
    response = APIClient().get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_health_is_read_only() -> None:
    response = APIClient().post("/api/health", {}, format="json")

    assert response.status_code == 405
