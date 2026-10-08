import uuid
from datetime import UTC, datetime

from fake_fetcher import DE_URL
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.email.recording import RecordingEmailSender
from app.models.alert import Alert
from app.services.alert_service import build_alert_service

USER_A = {"email": "alerts-a@example.com", "password": "supersecret1"}
USER_B = {"email": "alerts-b@example.com", "password": "supersecret2"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _matched_job(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    job = client.post("/api/v1/jobs", json={"url": DE_URL}, headers=headers).json()
    client.post(f"/api/v1/jobs/{job['id']}/match", headers=headers)
    return job


def _create_alert(client: TestClient, headers: dict[str, str], **overrides: object) -> dict:
    payload: dict[str, object] = {"name": "A", "min_overall": 0.0}
    payload.update(overrides)
    return client.post("/api/v1/alerts", json=payload, headers=headers).json()


def test_requires_auth(client: TestClient) -> None:
    assert client.post("/api/v1/alerts", json={"name": "x"}).status_code == 401
    assert client.get("/api/v1/alerts").status_code == 401
    assert client.post(f"/api/v1/alerts/{UNKNOWN}/preview").status_code == 401
    assert client.post(f"/api/v1/alerts/{UNKNOWN}/run").status_code == 401
    assert client.get(f"/api/v1/alerts/{UNKNOWN}/runs").status_code == 401


def test_crud_round_trip_and_isolation(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    created = _create_alert(client, headers, name="My alerts", frequency="weekly", min_overall=6.0)
    assert created["name"] == "My alerts"
    assert created["frequency"] == "weekly"
    assert created["unsubscribe_token"]
    assert created["next_run_at"] is not None

    assert len(client.get("/api/v1/alerts", headers=headers).json()) == 1

    updated = client.put(
        f"/api/v1/alerts/{created['id']}",
        json={"name": "Updated", "enabled": False, "frequency": "daily", "min_overall": 8.0},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is False

    assert client.delete(f"/api/v1/alerts/{created['id']}", headers=headers).status_code == 204
    assert client.get("/api/v1/alerts", headers=headers).json() == []

    headers_b = _headers(client, USER_B)
    assert client.get("/api/v1/alerts", headers=headers_b).json() == []


def test_preview_and_run_sends_digest(
    client: TestClient, recording_email: RecordingEmailSender
) -> None:
    headers = _headers(client, USER_A)
    _matched_job(client, headers)
    alert = _create_alert(client, headers)

    preview = client.post(f"/api/v1/alerts/{alert['id']}/preview", headers=headers)
    assert preview.status_code == 200
    assert len(preview.json()) == 1
    assert preview.json()[0]["title"] == "Data Engineer"

    run = client.post(f"/api/v1/alerts/{alert['id']}/run", headers=headers)
    assert run.status_code == 200
    assert run.json()["status"] == "ok"
    assert run.json()["items_count"] == 1
    assert len(recording_email.outbox) == 1
    assert "Data Engineer" in recording_email.outbox[0].text


def test_run_without_matches_is_skipped(
    client: TestClient, recording_email: RecordingEmailSender
) -> None:
    headers = _headers(client, USER_A)
    alert = _create_alert(client, headers)

    run = client.post(f"/api/v1/alerts/{alert['id']}/run", headers=headers).json()
    assert run["status"] == "skipped"
    assert run["items_count"] == 0
    assert recording_email.outbox == []


def test_run_alert_is_idempotent(
    client: TestClient, db_session: Session, recording_email: RecordingEmailSender
) -> None:
    headers = _headers(client, USER_A)
    _matched_job(client, headers)
    alert_id = _create_alert(client, headers)["id"]
    alert = db_session.get(Alert, uuid.UUID(alert_id))
    assert alert is not None

    service = build_alert_service(db_session, recording_email)
    when = datetime(2026, 1, 1, 10, tzinfo=UTC)
    first = service.run_alert(alert, scheduled_for=when)
    second = service.run_alert(alert, scheduled_for=when)

    assert first.id == second.id
    assert len(recording_email.outbox) == 1


def test_quiet_hours_suppresses_send(
    client: TestClient, db_session: Session, recording_email: RecordingEmailSender
) -> None:
    headers = _headers(client, USER_A)
    _matched_job(client, headers)
    alert_id = _create_alert(client, headers, quiet_hours_start=0, quiet_hours_end=23)["id"]
    alert = db_session.get(Alert, uuid.UUID(alert_id))
    assert alert is not None

    service = build_alert_service(db_session, recording_email)
    run = service.run_alert(alert, scheduled_for=datetime(2026, 1, 1, 10, tzinfo=UTC))

    assert run.status == "skipped"
    assert recording_email.outbox == []
    assert alert.next_run_at is not None


def test_unsubscribe_disables_alert(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    alert = _create_alert(client, headers)

    response = client.post(f"/api/v1/alerts/unsubscribe/{alert['unsubscribe_token']}")
    assert response.status_code == 200
    assert response.json() == {"unsubscribed": True}
    assert client.get(f"/api/v1/alerts/{alert['id']}", headers=headers).json()["enabled"] is False

    assert client.post("/api/v1/alerts/unsubscribe/nope").json() == {"unsubscribed": False}
