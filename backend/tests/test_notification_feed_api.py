import uuid

from fake_fetcher import DE_URL, REMOTE_URL
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.match import Match

USER_A = {"email": "notif-feed-a@example.com", "password": "supersecret1"}
USER_B = {"email": "notif-feed-b@example.com", "password": "supersecret2"}


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _seed(client: TestClient, db_session: Session) -> dict[str, str]:
    headers = _headers(client, USER_A)
    user_id = uuid.UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])

    # A strong match to review → a "match" notification.
    match_job = client.post("/api/v1/jobs", json={"url": DE_URL}, headers=headers).json()
    db_session.add(
        Match(
            user_id=user_id,
            job_id=uuid.UUID(match_job["id"]),
            overall=9.0,
            sub_scores={},
            recommendation="strong",
            excluded=False,
            reasons=[],
            evidence={},
            scoring_version="matching-v1",
        )
    )
    # An interview in progress → an "interview" notification.
    interview_job = client.post("/api/v1/jobs", json={"url": REMOTE_URL}, headers=headers).json()
    application = client.post(
        "/api/v1/applications", json={"job_id": interview_job["id"]}, headers=headers
    ).json()
    client.post(
        f"/api/v1/applications/{application['id']}/events",
        json={"type": "interview"},
        headers=headers,
    )
    db_session.commit()
    return headers


def test_feed_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/notifications").status_code == 401


def test_refresh_creates_then_is_idempotent(client: TestClient, db_session: Session) -> None:
    headers = _seed(client, db_session)

    first = client.post("/api/v1/notifications/refresh", headers=headers).json()
    assert first["created"] >= 2

    second = client.post("/api/v1/notifications/refresh", headers=headers).json()
    assert second["created"] == 0
    assert second["existing"] >= 2

    listed = client.get("/api/v1/notifications", headers=headers).json()
    assert {"match", "interview"} <= {item["kind"] for item in listed}


def test_unread_and_read_flow(client: TestClient, db_session: Session) -> None:
    headers = _seed(client, db_session)
    client.post("/api/v1/notifications/refresh", headers=headers)

    assert client.get("/api/v1/notifications/unread-count", headers=headers).json()["unread"] >= 2

    unread = client.get("/api/v1/notifications?unread=true", headers=headers).json()
    assert len(unread) >= 2

    marked = client.post(f"/api/v1/notifications/{unread[0]['id']}/read", headers=headers).json()
    assert marked["read_at"] is not None

    assert client.post("/api/v1/notifications/read-all", headers=headers).json()["unread"] == 0
    assert (
        client.delete(f"/api/v1/notifications/{unread[0]['id']}", headers=headers).status_code
        == 204
    )


def test_feed_isolated_per_user(client: TestClient, db_session: Session) -> None:
    headers_a = _seed(client, db_session)
    client.post("/api/v1/notifications/refresh", headers=headers_a)
    notification = client.get("/api/v1/notifications", headers=headers_a).json()[0]

    headers_b = _headers(client, USER_B)
    assert client.get("/api/v1/notifications", headers=headers_b).json() == []
    assert (
        client.post(
            f"/api/v1/notifications/{notification['id']}/read", headers=headers_b
        ).status_code
        == 404
    )
