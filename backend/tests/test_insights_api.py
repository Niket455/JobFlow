import json
import uuid
from datetime import UTC, datetime, timedelta

from fake_fetcher import DE_URL
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_gateway
from app.gateway.gateway import LLMGateway
from app.gateway.providers.mock_provider import MockProvider
from app.main import app
from app.models.application import Application
from app.models.job_analysis import JobAnalysis
from app.models.match import Match

USER_A = {"email": "insights-a@example.com", "password": "supersecret1"}
USER_B = {"email": "insights-b@example.com", "password": "supersecret2"}

ANALYSIS_JSON = json.dumps(
    {
        "skills_required": ["Python", "SQL", "Go"],
        "skills_preferred": ["PySpark"],
        "keywords": ["Airflow"],
    }
)


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _ingest(client: TestClient, headers: dict[str, str]) -> str:
    job = client.post("/api/v1/jobs", json={"url": DE_URL}, headers=headers).json()
    return str(job["id"])


def _use_analysis_gateway() -> None:
    app.dependency_overrides[get_gateway] = lambda: LLMGateway(
        MockProvider(ANALYSIS_JSON), max_retries=1
    )


def test_skill_gap_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/skill-gap").status_code == 401


def test_skill_gap_splits_have_and_missing(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    client.put("/api/v1/profile", json={"skills": ["Python", "SQL"]}, headers=headers)
    job_id = _ingest(client, headers)
    _use_analysis_gateway()
    assert client.post(f"/api/v1/jobs/{job_id}/analyze", headers=headers).status_code == 200

    report = client.get("/api/v1/skill-gap", headers=headers).json()

    assert report["total_jobs"] == 1
    have = {item["skill"] for item in report["have"]}
    missing = {item["skill"] for item in report["missing"]}
    assert {"Python", "SQL"} <= have
    assert {"Go", "PySpark", "Airflow"} <= missing
    assert report["missing"][0]["demand_pct"] == 100.0


def test_skill_gap_is_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    job_id = _ingest(client, headers_a)
    _use_analysis_gateway()
    client.post(f"/api/v1/jobs/{job_id}/analyze", headers=headers_a)

    headers_b = _headers(client, USER_B)
    report = client.get("/api/v1/skill-gap", headers=headers_b).json()
    assert report["total_jobs"] == 0
    assert report["missing"] == []


def test_daily_plan_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/daily-plan").status_code == 401


def test_daily_plan_review_and_learning(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    user_id = uuid.UUID(client.get("/api/v1/auth/me", headers=headers).json()["id"])
    job_id = _ingest(client, headers)

    db_session.add(
        Match(
            user_id=user_id,
            job_id=uuid.UUID(job_id),
            overall=9.0,
            sub_scores={},
            recommendation="strong",
            excluded=False,
            reasons=[],
            evidence={},
            scoring_version="matching-v1",
        )
    )
    db_session.add(JobAnalysis(job_id=uuid.UUID(job_id), data={"skills_required": ["Rust"]}))
    db_session.commit()

    plan = client.get("/api/v1/daily-plan", headers=headers).json()

    kinds = {item["kind"] for item in plan["items"]}
    assert {"review_job", "learning"} <= kinds
    assert plan["generated_from"]["strong_matches"] == 1
    assert len(plan["items"]) <= 12


def test_daily_plan_follow_up_then_interview(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    job_id = _ingest(client, headers)
    application = client.post(
        "/api/v1/applications", json={"job_id": job_id}, headers=headers
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

    kinds = {
        item["kind"] for item in client.get("/api/v1/daily-plan", headers=headers).json()["items"]
    }
    assert "follow_up" in kinds

    client.post(
        f"/api/v1/applications/{application['id']}/events",
        json={"type": "interview"},
        headers=headers,
    )
    kinds = {
        item["kind"] for item in client.get("/api/v1/daily-plan", headers=headers).json()["items"]
    }
    assert "interview_prep" in kinds
