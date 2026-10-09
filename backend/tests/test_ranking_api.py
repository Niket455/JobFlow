import uuid
from datetime import UTC, datetime

from fake_fetcher import DE_URL, REMOTE_URL
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.match import Match
from app.models.user import User
from app.services.ranking_service import build_ranking_service

USER_A = {"email": "ranking-a@example.com", "password": "supersecret1"}


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_ranking_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/ranking").status_code == 401
    assert client.post("/api/v1/ranking/reset").status_code == 401


def test_ranking_empty_and_reset(client: TestClient) -> None:
    headers = _headers(client, USER_A)

    body = client.get("/api/v1/ranking", headers=headers).json()
    assert body["items"] == []
    assert body["adjustments"] == []
    assert body["reset_at"] is None

    reset = client.post("/api/v1/ranking/reset", headers=headers).json()
    assert reset["reset_at"] is not None


def test_personalized_ranking_boosts_responsive_company(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "analytics_min_sample", 2)
    headers = _headers(client, USER_A)
    user_id = uuid.UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])

    first_job: dict = {}
    for url in (DE_URL, REMOTE_URL):
        job = client.post("/api/v1/jobs", json={"url": url}, headers=headers).json()
        application = client.post(
            "/api/v1/applications", json={"job_id": job["id"]}, headers=headers
        ).json()
        client.post(
            f"/api/v1/applications/{application['id']}/events",
            json={"type": "interview"},
            headers=headers,
        )
        first_job.setdefault("job", job)
    db_session.add(
        Match(
            user_id=user_id,
            job_id=uuid.UUID(first_job["job"]["id"]),
            overall=8.5,
            sub_scores={},
            recommendation="strong",
            excluded=False,
            reasons=[],
            evidence={},
            scoring_version="matching-v1",
        )
    )
    db_session.commit()

    report = client.get("/api/v1/ranking", headers=headers).json()

    assert report["adjustments"][0]["company"] == "Acme Inc"
    assert report["adjustments"][0]["response_rate"] == 1.0
    assert report["adjustments"][0]["boost"] == 1.0
    assert report["items"][0]["base"] == 8.5
    assert report["items"][0]["boost"] == 1.0
    assert report["items"][0]["score"] == 9.5


def test_reset_clears_personalization(client: TestClient, db_session: Session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "analytics_min_sample", 2)
    headers = _headers(client, USER_A)
    user_id = uuid.UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])
    for url in (DE_URL, REMOTE_URL):
        job = client.post("/api/v1/jobs", json={"url": url}, headers=headers).json()
        application = client.post(
            "/api/v1/applications", json={"job_id": job["id"]}, headers=headers
        ).json()
        client.post(
            f"/api/v1/applications/{application['id']}/events",
            json={"type": "interview"},
            headers=headers,
        )
    db_session.add(
        Match(
            user_id=user_id,
            job_id=uuid.UUID(client.get("/api/v1/jobs", headers=headers).json()[0]["id"]),
            overall=8.5,
            sub_scores={},
            recommendation="strong",
            excluded=False,
            reasons=[],
            evidence={},
            scoring_version="matching-v1",
        )
    )
    db_session.commit()

    user = db_session.get(User, user_id)
    assert user is not None
    service = build_ranking_service(db_session)
    service.reset(user, now=datetime.now(UTC))

    report = service.ranking(user, limit=10)
    assert report.adjustments == []
    assert report.items[0].boost == 0.0
