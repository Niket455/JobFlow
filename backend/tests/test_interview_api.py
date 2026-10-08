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
USER_A = {"email": "kit-a@example.com", "password": "supersecret1"}
USER_B = {"email": "kit-b@example.com", "password": "supersecret2"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"

KIT_JSON = json.dumps(
    {
        "questions": [
            {
                "category": "behavioral",
                "question": "Tell me about a time you led a project.",
                "intent": "leadership",
                "hint": "Use STAR",
                "answer_outline": ["Context", "Action", "Result"],
            },
            {
                "category": "technical",
                "question": "How do you optimize a slow SQL query?",
                "intent": "SQL depth",
                "hint": "Mention indexes",
                "answer_outline": ["Read the plan", "Add indexes"],
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


def _use_kit_gateway() -> None:
    app.dependency_overrides[get_gateway] = lambda: LLMGateway(
        MockProvider(KIT_JSON), max_retries=1
    )


def _generate(client: TestClient, headers: dict[str, str], job_id: str) -> dict:
    response = client.post("/api/v1/interview-kits", json={"job_id": job_id}, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_kit_requires_auth(client: TestClient) -> None:
    assert client.post("/api/v1/interview-kits", json={"job_id": UNKNOWN}).status_code == 401


def test_generate_and_fetch_kit(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _upload_resume(client, headers)
    job_id = _ingest(client, headers)
    _use_kit_gateway()

    kit = _generate(client, headers, job_id)
    assert len(kit["questions"]) == 2
    assert kit["questions"][0]["category"] == "behavioral"
    assert kit["questions"][1]["question"].startswith("How do you optimize")

    listed = client.get("/api/v1/interview-kits", headers=headers).json()
    assert len(listed) == 1
    assert listed[0]["question_count"] == 2

    fetched = client.get(f"/api/v1/interview-kits/{kit['id']}", headers=headers).json()
    assert fetched["questions"] == kit["questions"]


def test_generate_without_resume_is_404(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    job_id = _ingest(client, headers)
    _use_kit_gateway()
    response = client.post("/api/v1/interview-kits", json={"job_id": job_id}, headers=headers)
    assert response.status_code == 404


def test_kits_are_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    _upload_resume(client, headers_a)
    job_id = _ingest(client, headers_a)
    _use_kit_gateway()
    kit = _generate(client, headers_a, job_id)

    headers_b = _headers(client, USER_B)
    assert client.get(f"/api/v1/interview-kits/{kit['id']}", headers=headers_b).status_code == 404
    assert (
        client.post(
            "/api/v1/interview-kits", json={"job_id": job_id}, headers=headers_b
        ).status_code
        == 404
    )
