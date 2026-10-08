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
from app.models.resume_version import ResumeVersion

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
USER_A = {"email": "tailor-a@example.com", "password": "supersecret1"}
USER_B = {"email": "tailor-b@example.com", "password": "supersecret2"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"

TAILOR_JSON = json.dumps(
    {
        "changes": [
            {
                "path": "summary",
                "new_text": "Data engineer focused on Python and SQL.",
                "source_span": "Python SQL",
            },
            {
                "path": "current_role",
                "new_text": "Staff Engineer at Google",
                "source_span": "Google",
            },
        ]
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


def _use_tailor_gateway() -> None:
    app.dependency_overrides[get_gateway] = lambda: LLMGateway(
        MockProvider(TAILOR_JSON), max_retries=1
    )


def _tailor(client: TestClient, headers: dict[str, str], resume_id: str, job_id: str) -> dict:
    response = client.post(
        f"/api/v1/resumes/{resume_id}/tailor", json={"job_id": job_id}, headers=headers
    )
    assert response.status_code == 201
    return response.json()


def test_tailor_requires_auth(client: TestClient) -> None:
    response = client.post(f"/api/v1/resumes/{UNKNOWN}/tailor", json={"job_id": UNKNOWN})
    assert response.status_code == 401


def test_tailor_grounds_changes(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    resume_id = _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_tailor_gateway()

    run = _tailor(client, headers, resume_id, job_id)

    assert run["status"] == "proposed"
    changes = run["changes"]
    assert changes[0]["grounded"] is True
    assert changes[0]["decision"] == "approved"
    assert changes[0]["old_text"] == "Data engineer"
    assert changes[1]["path"] == "current_role"
    assert changes[1]["grounded"] is False
    assert changes[1]["decision"] == "rejected"


def test_apply_excludes_blocked_change(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    resume_id = _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_tailor_gateway()
    run = _tailor(client, headers, resume_id, job_id)

    applied = client.post(f"/api/v1/tailor-runs/{run['id']}/apply", headers=headers)
    assert applied.status_code == 200
    version = applied.json()
    assert version["parsed"]["summary"] == "Data engineer focused on Python and SQL."
    assert version["parsed"]["current_role"] is None
    assert version["label"].startswith("Tailored")

    row = db_session.get(ResumeVersion, uuid.UUID(version["id"]))
    assert row is not None
    assert str(row.parent_version_id) == resume_id


def test_approving_blocked_change_includes_it(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    resume_id = _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_tailor_gateway()
    run = _tailor(client, headers, resume_id, job_id)

    decided = client.post(
        f"/api/v1/tailor-runs/{run['id']}/decisions",
        json={"decisions": [{"index": 1, "decision": "approved"}]},
        headers=headers,
    )
    assert decided.status_code == 200
    assert decided.json()["changes"][1]["decision"] == "approved"

    applied = client.post(f"/api/v1/tailor-runs/{run['id']}/apply", headers=headers).json()
    assert applied["parsed"]["current_role"] == "Staff Engineer at Google"


def test_decision_index_out_of_range_is_400(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    resume_id = _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_tailor_gateway()
    run = _tailor(client, headers, resume_id, job_id)

    response = client.post(
        f"/api/v1/tailor-runs/{run['id']}/decisions",
        json={"decisions": [{"index": 99, "decision": "approved"}]},
        headers=headers,
    )
    assert response.status_code == 400


def test_reapply_returns_409(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    resume_id = _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_tailor_gateway()
    run = _tailor(client, headers, resume_id, job_id)

    assert client.post(f"/api/v1/tailor-runs/{run['id']}/apply", headers=headers).status_code == 200
    assert client.post(f"/api/v1/tailor-runs/{run['id']}/apply", headers=headers).status_code == 409


def test_runs_are_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    resume_id = _upload_resume(client, headers_a)
    job_id = _ingest(client, headers_a)
    _use_tailor_gateway()
    run = _tailor(client, headers_a, resume_id, job_id)

    headers_b = _headers(client, USER_B)
    assert client.get(f"/api/v1/tailor-runs/{run['id']}", headers=headers_b).status_code == 404
    assert (
        client.post(
            f"/api/v1/resumes/{resume_id}/tailor", json={"job_id": job_id}, headers=headers_b
        ).status_code
        == 404
    )
