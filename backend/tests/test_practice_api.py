import json
import uuid

from fake_fetcher import DE_URL
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_gateway
from app.gateway.gateway import LLMGateway
from app.gateway.providers.mock_provider import MockProvider
from app.main import app
from app.models.practice_session import PracticeSession

USER_A = {"email": "practice-a@example.com", "password": "supersecret1"}
USER_B = {"email": "practice-b@example.com", "password": "supersecret2"}

FEEDBACK_JSON = json.dumps(
    {
        "overall": 72,
        "criteria": [
            {"name": "STAR structure", "score": 4, "max_score": 5, "comment": "Clear arc."},
            {"name": "Impact and results", "score": 3, "max_score": 5, "comment": "Add metrics."},
        ],
        "strengths": ["Clear structure"],
        "improvements": ["Add measurable results"],
    }
)

ANSWER = "The situation was a slow pipeline. I rebuilt it and reduced runtime 40%."


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _use_feedback_gateway() -> None:
    app.dependency_overrides[get_gateway] = lambda: LLMGateway(
        MockProvider(FEEDBACK_JSON), max_retries=1
    )


def _evaluate(client: TestClient, headers: dict[str, str], **extra: object) -> dict:
    payload = {"question": "Tell me about a tough project.", "answer": ANSWER, **extra}
    response = client.post("/api/v1/practice-sessions", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_practice_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/practice-sessions", json={"question": "q", "answer": "a"})
    assert response.status_code == 401


def test_evaluate_returns_rubric_and_signals(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    _use_feedback_gateway()

    session = _evaluate(client, headers, duration_seconds=90)

    assert session["score"] == 72
    assert session["rubric"]["overall"] == 72
    assert session["rubric"]["criteria"][0]["name"] == "STAR structure"
    assert session["signals"]["has_metric"] is True
    assert session["signals"]["word_count"] > 0
    assert session["category"] == "general"
    assert session["duration_seconds"] == 90

    row = db_session.get(PracticeSession, uuid.UUID(session["id"]))
    assert row is not None
    assert row.answer_enc != ANSWER


def test_history_accumulates(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    _use_feedback_gateway()

    first = _evaluate(client, headers)
    second = _evaluate(client, headers)

    listed = client.get("/api/v1/practice-sessions", headers=headers).json()
    assert len(listed) == 2
    assert {item["id"] for item in listed} == {first["id"], second["id"]}

    fetched = client.get(f"/api/v1/practice-sessions/{first['id']}", headers=headers).json()
    assert fetched["answer"] == ANSWER


def test_optional_job_visibility(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    job = client.post("/api/v1/jobs", json={"url": DE_URL}, headers=headers_a).json()
    _use_feedback_gateway()

    assert _evaluate(client, headers_a, job_id=job["id"])["job_id"] == job["id"]

    headers_b = _headers(client, USER_B)
    response = client.post(
        "/api/v1/practice-sessions",
        json={"question": "q", "answer": "a", "job_id": job["id"]},
        headers=headers_b,
    )
    assert response.status_code == 404


def test_sessions_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    _use_feedback_gateway()
    session = _evaluate(client, headers_a)

    headers_b = _headers(client, USER_B)
    assert (
        client.get(f"/api/v1/practice-sessions/{session['id']}", headers=headers_b).status_code
        == 404
    )
