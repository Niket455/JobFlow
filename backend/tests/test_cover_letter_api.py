import io
import json
import uuid

from docx import Document
from fake_fetcher import DE_URL
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_gateway
from app.gateway.gateway import LLMGateway
from app.gateway.providers.mock_provider import MockProvider
from app.main import app
from app.models.cover_letter import CoverLetter

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
USER_A = {"email": "letter-a@example.com", "password": "supersecret1"}
USER_B = {"email": "letter-b@example.com", "password": "supersecret2"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"

COVER_LETTER_JSON = json.dumps(
    {
        "subject": "Application for Data Engineer",
        "body": "Dear team,\n\nI build pipelines with Python and SQL.\n\nI led work at Google.",
        "claims": [
            {"text": "I build pipelines with Python and SQL.", "source_span": "Python SQL"},
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


def _use_cover_gateway() -> None:
    app.dependency_overrides[get_gateway] = lambda: LLMGateway(
        MockProvider(COVER_LETTER_JSON), max_retries=1
    )


def _generate(client: TestClient, headers: dict[str, str], job_id: str) -> dict:
    response = client.post("/api/v1/cover-letters", json={"job_id": job_id}, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_generate_requires_auth(client: TestClient) -> None:
    assert client.post("/api/v1/cover-letters", json={"job_id": UNKNOWN}).status_code == 401


def test_generate_grounds_claims(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_cover_gateway()

    letter = _generate(client, headers, job_id)

    assert letter["subject"] == "Application for Data Engineer"
    assert "Python and SQL" in letter["body"]
    assert letter["claims"][0]["grounded"] is True
    assert letter["claims"][1]["grounded"] is False
    assert letter["blocked_count"] == 1
    assert letter["label"].startswith("Cover letter")


def test_body_is_encrypted_at_rest(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_cover_gateway()
    letter = _generate(client, headers, job_id)

    row = db_session.get(CoverLetter, uuid.UUID(letter["id"]))
    assert row is not None
    assert row.body_enc != letter["body"]
    assert "Python and SQL" not in row.body_enc


def test_list_and_get(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_cover_gateway()
    letter = _generate(client, headers, job_id)

    listed = client.get("/api/v1/cover-letters", headers=headers).json()
    assert len(listed) == 1
    assert listed[0]["id"] == letter["id"]
    assert "body" not in listed[0]

    fetched = client.get(f"/api/v1/cover-letters/{letter['id']}", headers=headers).json()
    assert fetched["body"] == letter["body"]


def test_missing_resume_is_404(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    job_id = _ingest(client, headers)
    _use_cover_gateway()
    response = client.post("/api/v1/cover-letters", json={"job_id": job_id}, headers=headers)
    assert response.status_code == 404


def test_unknown_job_is_404(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _upload_resume(client, headers)
    _use_cover_gateway()
    response = client.post("/api/v1/cover-letters", json={"job_id": UNKNOWN}, headers=headers)
    assert response.status_code == 404


def test_letters_are_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    resume_a = _upload_resume(client, headers_a)
    job_id = _ingest(client, headers_a)
    _use_cover_gateway()
    letter = _generate(client, headers_a, job_id)

    headers_b = _headers(client, USER_B)
    assert client.get(f"/api/v1/cover-letters/{letter['id']}", headers=headers_b).status_code == 404
    # User B cannot ground against user A's resume.
    response = client.post(
        "/api/v1/cover-letters",
        json={"job_id": job_id, "resume_version_id": resume_a},
        headers=headers_b,
    )
    assert response.status_code == 404


def test_list_filters_by_job_and_paginates(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_cover_gateway()
    _generate(client, headers, job_id)

    assert len(client.get(f"/api/v1/cover-letters?job_id={job_id}", headers=headers).json()) == 1
    assert client.get(f"/api/v1/cover-letters?job_id={UNKNOWN}", headers=headers).json() == []
    assert len(client.get("/api/v1/cover-letters?limit=1&offset=0", headers=headers).json()) == 1
    assert client.get("/api/v1/cover-letters?offset=1", headers=headers).json() == []


def test_revise_starts_a_new_version(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_cover_gateway()
    original = _generate(client, headers, job_id)

    response = client.post(
        f"/api/v1/cover-letters/{original['id']}/revise",
        json={"instructions": "Make it shorter"},
        headers=headers,
    )

    assert response.status_code == 201
    revised = response.json()
    assert revised["id"] != original["id"]
    assert revised["parent_letter_id"] == original["id"]
    assert revised["job_id"] == original["job_id"]
    assert len(client.get("/api/v1/cover-letters", headers=headers).json()) == 2


def test_revise_unknown_letter_is_404(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    response = client.post(f"/api/v1/cover-letters/{UNKNOWN}/revise", json={}, headers=headers)
    assert response.status_code == 404


def test_delete_letter(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_cover_gateway()
    letter = _generate(client, headers, job_id)

    assert (
        client.delete(f"/api/v1/cover-letters/{letter['id']}", headers=headers).status_code == 204
    )
    assert client.get(f"/api/v1/cover-letters/{letter['id']}", headers=headers).status_code == 404
    assert client.delete(f"/api/v1/cover-letters/{UNKNOWN}", headers=headers).status_code == 404


def test_revise_and_delete_are_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    _upload_resume(client, headers_a)
    job_id = _ingest(client, headers_a)
    _use_cover_gateway()
    letter = _generate(client, headers_a, job_id)

    headers_b = _headers(client, USER_B)
    revise = client.post(f"/api/v1/cover-letters/{letter['id']}/revise", json={}, headers=headers_b)
    assert revise.status_code == 404
    assert (
        client.delete(f"/api/v1/cover-letters/{letter['id']}", headers=headers_b).status_code == 404
    )


def test_decisions_gate_apply(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_cover_gateway()
    letter = _generate(client, headers, job_id)
    assert letter["blocked_count"] == 1

    blocked = client.post(f"/api/v1/cover-letters/{letter['id']}/apply", headers=headers)
    assert blocked.status_code == 409

    decided = client.post(
        f"/api/v1/cover-letters/{letter['id']}/decisions",
        json={"decisions": [{"index": 1, "decision": "approved"}]},
        headers=headers,
    )
    assert decided.status_code == 200
    assert decided.json()["blocked_count"] == 0

    applied = client.post(f"/api/v1/cover-letters/{letter['id']}/apply", headers=headers)
    assert applied.status_code == 200
    assert "I led work at Google." in applied.json()["body"]
    assert applied.json()["removed_claims"] == []


def test_apply_removes_rejected_claims(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_cover_gateway()
    letter = _generate(client, headers, job_id)

    client.post(
        f"/api/v1/cover-letters/{letter['id']}/decisions",
        json={"decisions": [{"index": 1, "decision": "rejected"}]},
        headers=headers,
    )
    applied = client.post(f"/api/v1/cover-letters/{letter['id']}/apply", headers=headers)

    assert applied.status_code == 200
    assert "I led work at Google." not in applied.json()["body"]
    assert applied.json()["removed_claims"] == ["I led work at Google."]


def test_bad_decision_index_is_400(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_cover_gateway()
    letter = _generate(client, headers, job_id)

    response = client.post(
        f"/api/v1/cover-letters/{letter['id']}/decisions",
        json={"decisions": [{"index": 9, "decision": "approved"}]},
        headers=headers,
    )
    assert response.status_code == 400
