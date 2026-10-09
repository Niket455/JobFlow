from fake_fetcher import BLOCKED_URL, DE_URL
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application import Application
from app.models.job_source import JobSource

USER_A = {"email": "capture-a@example.com", "password": "supersecret1"}
USER_B = {"email": "capture-b@example.com", "password": "supersecret2"}


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _capture(client: TestClient, headers: dict[str, str], url: str, **overrides: object):
    payload: dict[str, object] = {"url": url}
    payload.update(overrides)
    return client.post("/api/v1/jobs/capture", json=payload, headers=headers)


def test_capture_requires_auth(client: TestClient) -> None:
    assert client.post("/api/v1/jobs/capture", json={"url": DE_URL}).status_code == 401


def test_capture_creates_job_and_saved_application(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)

    response = _capture(client, headers, DE_URL)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "Saved"
    assert body["kanban"] == "Saved"
    assert [event["type"] for event in body["events"]] == ["saved"]
    assert db_session.scalar(select(JobSource).where(JobSource.adapter == "user_url")) is not None


def test_capture_with_applied_at_marks_applied(client: TestClient) -> None:
    headers = _headers(client, USER_A)

    response = _capture(client, headers, DE_URL, applied_at="2026-01-01T00:00:00Z")

    assert response.status_code == 201
    assert response.json()["status"] == "Applied"


def test_recapture_is_idempotent(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)

    first = _capture(client, headers, DE_URL)
    second = _capture(client, headers, DE_URL)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert db_session.scalar(select(func.count()).select_from(Application)) == 1


def test_existing_application_still_conflicts(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _capture(client, headers, DE_URL)
    job = client.get("/api/v1/jobs", headers=headers).json()[0]

    response = client.post("/api/v1/applications", json={"job_id": job["id"]}, headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"]["application_id"]


def test_capture_unfetchable_url_is_502(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    assert _capture(client, headers, "https://jobs.example.com/ghost").status_code == 502


def test_capture_robots_blocked_is_403(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    assert _capture(client, headers, BLOCKED_URL).status_code == 403


def test_capture_disabled_flag_returns_403(client: TestClient, monkeypatch) -> None:
    headers = _headers(client, USER_A)
    monkeypatch.setattr(settings, "enable_user_url_ingestion", False)
    assert _capture(client, headers, DE_URL).status_code == 403


def test_capture_is_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    headers_b = _headers(client, USER_B)

    a = _capture(client, headers_a, DE_URL).json()
    b = _capture(client, headers_b, DE_URL).json()

    assert a["id"] != b["id"]
    assert len(client.get("/api/v1/applications", headers=headers_a).json()) == 1
    assert len(client.get("/api/v1/applications", headers=headers_b).json()) == 1
