import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.email.recording import RecordingEmailSender
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_delivery_service import build_notification_delivery_service

USER_A = {"email": "deliver-a@example.com", "password": "supersecret1"}


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _user(db_session: Session, email: str) -> User:
    user = User(email=email, password_hash="x")
    db_session.add(user)
    db_session.commit()
    return user


def _notification(db_session: Session, user_id: uuid.UUID, key: str) -> None:
    db_session.add(Notification(user_id=user_id, kind="match", title="New match", dedupe_key=key))
    db_session.commit()


def test_deliver_pending_sends_once(db_session: Session) -> None:
    sender = RecordingEmailSender()
    user = _user(db_session, "deliver@example.com")
    _notification(db_session, user.id, "m1")
    service = build_notification_delivery_service(db_session, sender)
    now = datetime(2026, 1, 1, tzinfo=UTC)

    assert service.deliver_pending(user, now=now) == 1
    assert len(sender.outbox) == 1
    assert service.deliver_pending(user, now=now) == 0


def test_deliver_all_across_users(db_session: Session) -> None:
    sender = RecordingEmailSender()
    _notification(db_session, _user(db_session, "a@example.com").id, "a1")
    _notification(db_session, _user(db_session, "b@example.com").id, "b1")
    service = build_notification_delivery_service(db_session, sender)

    assert service.deliver_all(now=datetime(2026, 1, 1, tzinfo=UTC), limit=10) == 2
    assert len(sender.outbox) == 2


def test_deliver_endpoint(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    user_id = uuid.UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])
    _notification(db_session, user_id, "k1")

    response = client.post("/api/v1/notifications/deliver", headers=headers)

    assert response.status_code == 200
    assert response.json()["delivered"] == 1


def test_delivery_task_is_registered() -> None:
    from app.workers.tasks import deliver_notification_emails

    assert deliver_notification_emails.name == "app.workers.tasks.deliver_notification_emails"
