from fastapi.testclient import TestClient

from worktrace_agent import __version__
from worktrace_agent.api.app import create_app


def test_health_returns_sidecar_status() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "app_name": "worktrace-local-agent",
        "app_version": __version__,
        "schema_version": "004_session_organization.sql",
        "status": "ok",
    }


def test_health_route_is_included_in_openapi_schema() -> None:
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]
