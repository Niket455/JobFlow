from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_sets_request_id(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers.get("X-Request-ID")


def test_ready_reports_checks(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code in (200, 503)
    body = response.json()
    assert body["checks"]["database"] == "ok"
