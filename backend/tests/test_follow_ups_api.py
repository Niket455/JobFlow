import uuid
from datetime import UTC, datetime, timedelta

from fake_fetcher import DE_URL
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.application import Application

USER_A = {"email": "followups-a@example.com", "password": "supersecret1"}
USER_B = {"email": "followups-b@example.com", "password": "supersecret2"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _aging_application(client: TestClient, db_session: Session, headers: dict[str, str]) -> str:
    job = client.post("/api/v1/jobs", json={"url": DE_URL}, headers=headers).json()
    application = client.post(
        "/api/v1/applications", json={"job_id": job["id"]}, headers=headers
    ).json()
    client.post(
        f"/api/v1/applications/{application['id']}/events",
        json={"type": "applied"},
        headers=headers,
    )
    row = db_session.get(Application, uuid.UUID(application["id"]))
    assert row is not None
    row.updated_at = datetime.now(UTC) - timedelta(days=10)
    db_session.commit()
    return str(application["id"])


def test_follow_ups_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/follow-ups").status_code == 401
    assert client.post(f"/api/v1/follow-ups/{UNKNOWN}/snooze", json={"days": 3}).status_code == 401
    assert client.post(f"/api/v1/follow-ups/{UNKNOWN}/done").status_code == 401


def test_stale_application_is_a_follow_up(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    application_id = _aging_application(client, db_session, headers)

    body = client.get("/api/v1/follow-ups", headers=headers).json()

    assert body["generated_from"]["follow_ups"] == 1
    assert body["items"][0]["application_id"] == application_id
    assert body["items"][0]["action"] == "Follow up"
    assert body["items"][0]["days_since_update"] >= 10


def test_interview_becomes_prepare(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    application_id = _aging_application(client, db_session, headers)
    client.post(
        f"/api/v1/applications/{application_id}/events",
        json={"type": "interview"},
        headers=headers,
    )

    body = client.get("/api/v1/follow-ups", headers=headers).json()

    assert body["items"][0]["action"] == "Prepare"
    assert body["items"][0]["status"] == "Interview"


def test_follow_ups_isolated_per_user(client: TestClient, db_session: Session) -> None:
    headers_a = _headers(client, USER_A)
    application_id = _aging_application(client, db_session, headers_a)

    headers_b = _headers(client, USER_B)
    assert client.get("/api/v1/follow-ups", headers=headers_b).json()["items"] == []
    response = client.post(f"/api/v1/follow-ups/{application_id}/done", headers=headers_b)
    assert response.status_code == 404


def test_snooze_hides_the_follow_up(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    application_id = _aging_application(client, db_session, headers)
    assert client.get("/api/v1/follow-ups", headers=headers).json()["items"]

    response = client.post(
        f"/api/v1/follow-ups/{application_id}/snooze", json={"days": 5}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["application_id"] == application_id
    assert response.json()["snoozed_until"] is not None
    assert client.get("/api/v1/follow-ups", headers=headers).json()["items"] == []


def test_mark_done_resets_the_clock(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    application_id = _aging_application(client, db_session, headers)
    assert client.get("/api/v1/follow-ups", headers=headers).json()["items"]

    response = client.post(f"/api/v1/follow-ups/{application_id}/done", headers=headers)

    assert response.status_code == 200
    assert response.json()["followed_up_at"] is not None
    assert client.get("/api/v1/follow-ups", headers=headers).json()["items"] == []


def test_follow_up_actions_unknown_application_404(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    snooze = client.post(f"/api/v1/follow-ups/{UNKNOWN}/snooze", json={"days": 3}, headers=headers)
    assert snooze.status_code == 404
    assert client.post(f"/api/v1/follow-ups/{UNKNOWN}/done", headers=headers).status_code == 404
