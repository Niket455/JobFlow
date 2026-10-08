import json

from fake_fetcher import DE_URL
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_gateway
from app.gateway.gateway import LLMGateway
from app.gateway.providers.mock_provider import MockProvider
from app.main import app
from app.models.job_analysis import JobAnalysis

ANALYSIS_JSON = json.dumps(
    {
        "skills_required": ["Python", "SQL"],
        "skills_preferred": ["PySpark"],
        "responsibilities": ["Build data pipelines"],
        "seniority": "Senior",
        "keywords": ["data engineering"],
        "confidence": {"skills_required": 0.9, "seniority": 0.6},
        "source_snippets": {"skills_required": "Python, SQL"},
    }
)

USER_A = {"email": "analysis-a@example.com", "password": "supersecret1"}
USER_B = {"email": "analysis-b@example.com", "password": "supersecret2"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _ingest(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    return client.post("/api/v1/jobs", json={"url": DE_URL}, headers=headers).json()


def _use_analysis_gateway() -> None:
    app.dependency_overrides[get_gateway] = lambda: LLMGateway(
        MockProvider(ANALYSIS_JSON), max_retries=1
    )


def test_analyze_requires_auth(client: TestClient) -> None:
    assert client.post(f"/api/v1/jobs/{UNKNOWN}/analyze").status_code == 401


def test_analyze_and_get(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    job = _ingest(client, headers)
    _use_analysis_gateway()

    response = client.post(f"/api/v1/jobs/{job['id']}/analyze", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job["id"]
    assert body["skills_required"] == ["Python", "SQL"]
    assert body["skills_preferred"] == ["PySpark"]
    assert body["seniority"] == "Senior"
    assert body["confidence"]["skills_required"] == 0.9

    fetched = client.get(f"/api/v1/jobs/{job['id']}/analysis", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["responsibilities"] == ["Build data pipelines"]

    assert db_session.scalar(select(func.count()).select_from(JobAnalysis)) == 1


def test_get_analysis_before_analyze_returns_404(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    job = _ingest(client, headers)
    assert client.get(f"/api/v1/jobs/{job['id']}/analysis", headers=headers).status_code == 404


def test_analyze_foreign_job_returns_404(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    job = _ingest(client, headers_a)

    headers_b = _headers(client, USER_B)
    response = client.post(f"/api/v1/jobs/{job['id']}/analyze", headers=headers_b)
    assert response.status_code == 404


def test_reanalyze_upserts_single_row(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    job = _ingest(client, headers)
    _use_analysis_gateway()

    client.post(f"/api/v1/jobs/{job['id']}/analyze", headers=headers)
    client.post(f"/api/v1/jobs/{job['id']}/analyze", headers=headers)

    assert db_session.scalar(select(func.count()).select_from(JobAnalysis)) == 1
