import io
import json
import uuid

from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_gateway
from app.gateway.gateway import LLMGateway
from app.gateway.providers.mock_provider import MockProvider
from app.main import app
from app.models.star_story import StarStory

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
USER_A = {"email": "star-a@example.com", "password": "supersecret1"}
USER_B = {"email": "star-b@example.com", "password": "supersecret2"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"

RESUME_JSON = json.dumps(
    {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "skills": ["Python", "SQL"],
        "work_history": [
            {
                "company": "Acme",
                "title": "Data Engineer",
                "description": "Built pipelines that cut latency 40%.",
            }
        ],
        "confidence": {"personal": 0.9},
    }
)

STAR_JSON = json.dumps(
    {
        "title": "Cut pipeline latency at Acme",
        "situation": "A legacy pipeline was slow.",
        "task": "I needed to speed it up.",
        "action": "I rebuilt it with batch processing.",
        "result": "Runtime dropped 40%.",
        "skills": ["Python", "SQL"],
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


def _use_gateway(payload: str) -> None:
    app.dependency_overrides[get_gateway] = lambda: LLMGateway(MockProvider(payload), max_retries=1)


def _upload_resume(client: TestClient, headers: dict[str, str]) -> str:
    files = {"file": ("resume.docx", _docx_bytes("Jane Doe Python SQL"), DOCX_CONTENT_TYPE)}
    response = client.post("/api/v1/resumes", files=files, headers=headers)
    assert response.status_code == 201
    return str(response.json()["id"])


def _create_story(client: TestClient, headers: dict[str, str], **extra: object) -> dict:
    body = {
        "title": "Latency win",
        "situation": "A legacy pipeline was slow.",
        "task": "Speed it up.",
        "action": "I rebuilt it.",
        "result": "Runtime dropped 40%.",
        "skills": ["Python"],
        **extra,
    }
    response = client.post("/api/v1/star-stories", json=body, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_star_create_requires_auth(client: TestClient) -> None:
    assert client.post("/api/v1/star-stories", json={"title": "x"}).status_code == 401


def test_create_links_to_resume_item(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    _use_gateway(RESUME_JSON)
    resume_id = _upload_resume(client, headers)

    story = _create_story(
        client,
        headers,
        resume_version_id=resume_id,
        resume_item_path="work_history.0",
    )
    assert story["resume_item_path"] == "work_history.0"
    assert story["result"] == "Runtime dropped 40%."

    row = db_session.get(StarStory, uuid.UUID(story["id"]))
    assert row is not None
    assert row.content_enc != story["situation"]


def test_invalid_resume_path_is_400(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _use_gateway(RESUME_JSON)
    resume_id = _upload_resume(client, headers)

    response = client.post(
        "/api/v1/star-stories",
        json={
            "title": "Bad link",
            "resume_version_id": resume_id,
            "resume_item_path": "work_history.9",
        },
        headers=headers,
    )
    assert response.status_code == 400


def test_path_without_resume_is_400(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    response = client.post(
        "/api/v1/star-stories",
        json={"title": "Bad link", "resume_item_path": "summary"},
        headers=headers,
    )
    assert response.status_code == 400


def test_update_and_delete(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    story = _create_story(client, headers)

    updated = client.put(
        f"/api/v1/star-stories/{story['id']}", json={"result": "Runtime halved."}, headers=headers
    ).json()
    assert updated["result"] == "Runtime halved."
    assert updated["situation"] == "A legacy pipeline was slow."

    assert client.delete(f"/api/v1/star-stories/{story['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/star-stories/{story['id']}", headers=headers).status_code == 404


def test_draft_from_resume_item(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _use_gateway(RESUME_JSON)
    resume_id = _upload_resume(client, headers)
    _use_gateway(STAR_JSON)

    response = client.post(
        "/api/v1/star-stories/draft",
        json={"resume_version_id": resume_id, "path": "work_history.0"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Cut pipeline latency at Acme"
    assert response.json()["result"] == "Runtime dropped 40%."


def test_stories_are_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    story = _create_story(client, headers_a)

    headers_b = _headers(client, USER_B)
    assert client.get(f"/api/v1/star-stories/{story['id']}", headers=headers_b).status_code == 404
    assert (
        client.put(
            f"/api/v1/star-stories/{story['id']}", json={"title": "hijack"}, headers=headers_b
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/v1/star-stories/{story['id']}", headers=headers_b).status_code == 404
    )
