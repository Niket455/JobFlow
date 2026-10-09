import uuid
from datetime import UTC, datetime, timedelta

from fake_fetcher import DE_URL
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.application import Application
from app.services.notification_center_service import build_notification_center_service

USER_A = {"email": "nrefresh-a@example.com", "password": "supersecret1"}
USER_B = {"email": "nrefresh-b@example.com", "password": "supersecret2"}


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _stale_application(
    client: TestClient, db_session: Session, credentials: dict[str, str], *, now: datetime
) -> None:
    headers = _headers(client, credentials)
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
    row.updated_at = now - timedelta(days=10)
    db_session.commit()


def test_refresh_all_creates_then_is_idempotent(client: TestClient, db_session: Session) -> None:
    now = datetime.now(UTC)
    _stale_application(client, db_session, USER_A, now=now)
    _stale_application(client, db_session, USER_B, now=now)

    service = build_notification_center_service(db_session)

    first = service.refresh_all(now=now, limit=10)
    second = service.refresh_all(now=now, limit=10)

    assert first >= 2  # at least one follow_up notification per stale user
    assert second == 0  # idempotent on re-run


def test_refresh_task_is_registered() -> None:
    from app.workers.tasks import refresh_notifications

    assert refresh_notifications.name == "app.workers.tasks.refresh_notifications"
