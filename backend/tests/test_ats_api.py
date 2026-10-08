import io
import json

from docx import Document
from fake_fetcher import DE_URL
from fastapi.testclient import TestClient

from app.api.deps import get_gateway
from app.gateway.gateway import LLMGateway
from app.gateway.providers.mock_provider import MockProvider
from app.main import app

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
USER_A = {"email": "atsreport-a@example.com", "password": "supersecret1"}
USER_B = {"email": "atsreport-b@example.com", "password": "supersecret2"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"

ANALYSIS_JSON = json.dumps(
    {
        "skills_required": ["Python", "SQL", "Go"],
        "keywords": ["Airflow"],
        "seniority": "Senior",
    }
)


def _docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _upload_resume(client: TestClient, headers: dict[str, str]) -> str:
    files = {"file": ("resume.docx", _docx_bytes("Jane Doe Python SQL"), DOCX_CONTENT_TYPE)}
    response = client.post("/api/v1/resumes", files=files, headers=headers)
    assert response.status_code == 201
    return str(response.json()["id"])


def _ingest(client: TestClient, headers: dict[str, str]) -> str:
    job = client.post("/api/v1/jobs", json={"url": DE_URL}, headers=headers).json()
    return str(job["id"])


def _use_analysis_gateway() -> None:
    app.dependency_overrides[get_gateway] = lambda: LLMGateway(
        MockProvider(ANALYSIS_JSON), max_retries=1
    )


def test_ats_report_requires_auth(client: TestClient) -> None:
    assert client.get(f"/api/v1/resumes/{UNKNOWN}/ats-report").status_code == 401


def test_ats_report_parses_resume(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    resume_id = _upload_resume(client, headers)

    response = client.get(f"/api/v1/resumes/{resume_id}/ats-report", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["score"] <= 100
    assert body["grade"] in {"A", "B", "C", "D", "F"}
    assert body["parse_test"]["passed"] is True
    assert body["keywords"] is None
    assert any(check["id"] == "parse_docx" for check in body["checks"])


def test_ats_report_with_job_keywords(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    resume_id = _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_analysis_gateway()
    assert client.post(f"/api/v1/jobs/{job_id}/analyze", headers=headers).status_code == 200

    body = client.get(
        f"/api/v1/resumes/{resume_id}/ats-report?job_id={job_id}", headers=headers
    ).json()
    assert body["keywords"] is not None
    assert "Python" in body["keywords"]["matched"]
    assert "Go" in body["keywords"]["missing"]


def test_ats_report_unknown_resume_404(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    assert client.get(f"/api/v1/resumes/{UNKNOWN}/ats-report", headers=headers).status_code == 404


def test_ats_report_foreign_job_404(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    job_id = _ingest(client, headers_a)

    headers_b = _headers(client, USER_B)
    resume_b = _upload_resume(client, headers_b)
    response = client.get(
        f"/api/v1/resumes/{resume_b}/ats-report?job_id={job_id}", headers=headers_b
    )
    assert response.status_code == 404
