import uuid

from fake_fetcher import DE_URL
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.job_analysis import JobAnalysis
from app.models.match import Match

USER_A = {"email": "cc-a@example.com", "password": "supersecret1"}


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _seed(client: TestClient, db_session: Session) -> tuple[dict, str]:
    headers = _headers(client, USER_A)
    user_id = uuid.UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])
    client.put("/api/v1/career-goals", json={"target_role": "Data Engineer"}, headers=headers)
    client.put("/api/v1/profile", json={"skills": ["Python"]}, headers=headers)
    job = client.post("/api/v1/jobs", json={"url": DE_URL}, headers=headers).json()

    db_session.add(
        JobAnalysis(job_id=uuid.UUID(job["id"]), data={"skills_required": ["Go", "Rust"]})
    )
    db_session.add(
        Match(
            user_id=user_id,
            job_id=uuid.UUID(job["id"]),
            overall=9.0,
            sub_scores={},
            recommendation="strong",
            excluded=False,
            reasons=[],
            evidence={},
            scoring_version="matching-v1",
        )
    )
    db_session.commit()
    return headers, str(job["id"])


def test_command_center_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/command-center").status_code == 401
    assert client.get("/api/v1/learning-roadmap").status_code == 401


def test_learning_roadmap_from_skill_gap(client: TestClient, db_session: Session) -> None:
    headers, _ = _seed(client, db_session)

    roadmap = client.get("/api/v1/learning-roadmap", headers=headers).json()

    assert roadmap["total_jobs"] == 1
    assert [item["skill"] for item in roadmap["items"]] == ["Go", "Rust"]
    assert roadmap["items"][0]["priority"] == 1


def test_command_center_aggregates(client: TestClient, db_session: Session) -> None:
    headers, _ = _seed(client, db_session)

    body = client.get("/api/v1/command-center", headers=headers).json()

    assert body["goal"]["target_role"] == "Data Engineer"
    assert body["funnel"]["total"] == 0
    assert body["counts"]["tracked_jobs"] == 1
    assert body["counts"]["strong_matches"] == 1
    assert body["counts"]["skill_gaps"] == 2

    kinds = {item["kind"] for item in body["today"]["items"]}
    assert {"review_job", "learning"} <= kinds

    assert body["insight"]["headline"] == "Close the Go gap"
    assert body["insight"]["evidence"][0]["kind"] == "skill"


def test_command_center_surfaces_interview(client: TestClient, db_session: Session) -> None:
    headers, job_id = _seed(client, db_session)
    application = client.post(
        "/api/v1/applications", json={"job_id": job_id}, headers=headers
    ).json()
    client.post(
        f"/api/v1/applications/{application['id']}/events",
        json={"type": "applied"},
        headers=headers,
    )
    client.post(
        f"/api/v1/applications/{application['id']}/events",
        json={"type": "interview"},
        headers=headers,
    )

    body = client.get("/api/v1/command-center", headers=headers).json()

    assert "interview" in body["insight"]["headline"].lower()
    assert body["insight"]["evidence"][0]["kind"] == "application"
    assert any(item["kind"] == "interview_prep" for item in body["today"]["items"])
