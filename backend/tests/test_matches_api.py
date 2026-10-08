import json
import uuid

from fake_fetcher import DE_URL, REMOTE_URL
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_gateway
from app.gateway.gateway import LLMGateway
from app.gateway.providers.mock_provider import MockProvider
from app.main import app
from app.models.job import Job
from app.models.job_analysis import JobAnalysis
from app.models.match import Match

USER_A = {"email": "match-a@example.com", "password": "supersecret1"}
USER_B = {"email": "match-b@example.com", "password": "supersecret2"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"

ANALYSIS_JSON = json.dumps(
    {"skills_required": ["Python", "SQL"], "skills_preferred": ["PySpark"], "seniority": "Senior"}
)


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _ingest(client: TestClient, headers: dict[str, str], url: str) -> dict[str, object]:
    return client.post("/api/v1/jobs", json={"url": url}, headers=headers).json()


def _seed_analysis(db_session: Session, job_id: object, **overrides: object) -> None:
    data: dict[str, object] = {
        "skills_required": ["Python", "SQL"],
        "skills_preferred": ["PySpark"],
        "seniority": "Senior",
        "keywords": ["data engineer"],
    }
    data.update(overrides)
    db_session.add(JobAnalysis(job_id=uuid.UUID(str(job_id)), data=data))
    db_session.commit()


def _set_profile(client: TestClient, headers: dict[str, str]) -> None:
    client.put(
        "/api/v1/profile",
        json={"skills": ["Python", "SQL"], "experience_years": 6},
        headers=headers,
    )
    client.put(
        "/api/v1/career-goals",
        json={"target_role": "Data Engineer", "locations": ["Bengaluru"]},
        headers=headers,
    )


def test_match_requires_auth(client: TestClient) -> None:
    assert client.post(f"/api/v1/jobs/{UNKNOWN}/match").status_code == 401
    assert client.get("/api/v1/matches").status_code == 401
    assert client.post("/api/v1/matches/recompute").status_code == 401


def test_match_job_returns_score_and_evidence(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    _set_profile(client, headers)
    job = _ingest(client, headers, DE_URL)
    _seed_analysis(db_session, job["id"])

    response = client.post(f"/api/v1/jobs/{job['id']}/match", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job["id"]
    assert body["scoring_version"] == "matching-v1"
    assert body["sub_scores"]["skills"] == 8.0
    assert body["sub_scores"]["location"] == 10.0
    assert body["evidence"]["matched"] == ["Python", "SQL"]
    assert body["recommendation"] in {"strong", "good", "partial", "weak"}
    assert db_session.query(Match).count() == 1


def test_match_unknown_or_foreign_job_returns_404(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    job = _ingest(client, headers_a, DE_URL)

    assert client.post(f"/api/v1/jobs/{UNKNOWN}/match", headers=headers_a).status_code == 404

    headers_b = _headers(client, USER_B)
    assert client.post(f"/api/v1/jobs/{job['id']}/match", headers=headers_b).status_code == 404


def test_recompute_skips_non_active_jobs(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    _set_profile(client, headers)
    active = _ingest(client, headers, DE_URL)
    expired = _ingest(client, headers, REMOTE_URL)

    row = db_session.get(Job, uuid.UUID(str(expired["id"])))
    assert row is not None
    row.status = "Expired"
    db_session.commit()

    response = client.post("/api/v1/matches/recompute", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"recomputed": 1}

    listing = client.get("/api/v1/matches", headers=headers).json()
    assert len(listing) == 1
    assert listing[0]["job_id"] == active["id"]


def test_list_and_get_matches_are_isolated(client: TestClient, db_session: Session) -> None:
    headers_a = _headers(client, USER_A)
    _set_profile(client, headers_a)
    job = _ingest(client, headers_a, DE_URL)
    _seed_analysis(db_session, job["id"])
    client.post("/api/v1/matches/recompute", headers=headers_a)

    listing = client.get("/api/v1/matches", headers=headers_a).json()
    assert len(listing) == 1

    detail = client.get(f"/api/v1/matches/{listing[0]['id']}", headers=headers_a)
    assert detail.status_code == 200
    assert detail.json()["evidence"]["matched"] == ["Python", "SQL"]

    headers_b = _headers(client, USER_B)
    assert client.get("/api/v1/matches", headers=headers_b).json() == []
    assert client.get(f"/api/v1/matches/{listing[0]['id']}", headers=headers_b).status_code == 404


def test_match_uses_analysis_produced_by_analyze(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _set_profile(client, headers)
    job = _ingest(client, headers, DE_URL)

    app.dependency_overrides[get_gateway] = lambda: LLMGateway(
        MockProvider(ANALYSIS_JSON), max_retries=1
    )
    assert client.post(f"/api/v1/jobs/{job['id']}/analyze", headers=headers).status_code == 200

    response = client.post(f"/api/v1/jobs/{job['id']}/match", headers=headers)
    assert response.status_code == 200
    assert response.json()["sub_scores"]["skills"] == 8.0
