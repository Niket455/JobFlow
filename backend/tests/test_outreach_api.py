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
USER_A = {"email": "outreach-a@example.com", "password": "supersecret1"}
USER_B = {"email": "outreach-b@example.com", "password": "supersecret2"}

OUTREACH_JSON = json.dumps(
    {
        "subject": "Quick question about the Data Engineer role",
        "body": "Hi Sam,\n\nI work with Python and SQL. I previously led work at Google.",
        "claims": [
            {"text": "I work with Python and SQL.", "source_span": "Python SQL"},
            {"text": "I led work at Google.", "source_span": "Google"},
        ],
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


def _create_contact(client: TestClient, headers: dict[str, str]) -> str:
    body = {"name": "Sam Recruiter", "relationship": "referral", "company_name": "Acme"}
    contact = client.post("/api/v1/contacts", json=body, headers=headers).json()
    return str(contact["id"])


def _use_outreach_gateway() -> None:
    app.dependency_overrides[get_gateway] = lambda: LLMGateway(
        MockProvider(OUTREACH_JSON), max_retries=1
    )


def _generate(client: TestClient, headers: dict[str, str], contact_id: str, job_id: str) -> dict:
    payload = {"contact_id": contact_id, "job_id": job_id, "kind": "referral"}
    response = client.post("/api/v1/outreach-drafts", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_outreach_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/v1/outreach-drafts", json={"contact_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert response.status_code == 401


def test_generate_grounds_claims(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    contact_id = _create_contact(client, headers)
    _use_outreach_gateway()

    draft = _generate(client, headers, contact_id, job_id)

    assert draft["status"] == "draft"
    assert draft["kind"] == "referral"
    assert "Python and SQL" in draft["body"]
    assert draft["claims"][0]["grounded"] is True
    assert draft["claims"][1]["grounded"] is False
    assert draft["blocked_count"] == 1

    listed = client.get("/api/v1/outreach-drafts", headers=headers).json()
    assert len(listed) == 1
    assert listed[0]["id"] == draft["id"]

    fetched = client.get(f"/api/v1/outreach-drafts/{draft['id']}", headers=headers).json()
    assert fetched["body"] == draft["body"]


def test_send_marks_contact_contacted(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    contact_id = _create_contact(client, headers)
    _use_outreach_gateway()
    draft = _generate(client, headers, contact_id, job_id)

    sent = client.post(f"/api/v1/outreach-drafts/{draft['id']}/send", headers=headers).json()
    assert sent["status"] == "sent"

    contact = client.get(f"/api/v1/contacts/{contact_id}", headers=headers).json()
    assert contact["last_contacted_at"] is not None


def test_generate_unknown_contact_404(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _use_outreach_gateway()
    response = client.post(
        "/api/v1/outreach-drafts",
        json={"contact_id": "00000000-0000-0000-0000-000000000000", "kind": "referral"},
        headers=headers,
    )
    assert response.status_code == 404


def test_outreach_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    _upload_resume(client, headers_a)
    job_id = _ingest(client, headers_a)
    contact_id = _create_contact(client, headers_a)
    _use_outreach_gateway()
    draft = _generate(client, headers_a, contact_id, job_id)

    headers_b = _headers(client, USER_B)
    assert (
        client.get(f"/api/v1/outreach-drafts/{draft['id']}", headers=headers_b).status_code == 404
    )
