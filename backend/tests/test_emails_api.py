import json

from fake_fetcher import DE_URL
from fastapi.testclient import TestClient

from app.api.deps import get_gateway
from app.gateway.gateway import LLMGateway
from app.gateway.providers.mock_provider import MockProvider
from app.main import app

USER_A = {"email": "emails-a@example.com", "password": "supersecret1"}
USER_B = {"email": "emails-b@example.com", "password": "supersecret2"}

INTERVIEW_JSON = json.dumps(
    {
        "classification": "interview",
        "confidence": 0.9,
        "suggested_event": "interview",
        "rationale": "Schedules an interview.",
    }
)
REJECTION_JSON = json.dumps(
    {
        "classification": "rejection",
        "confidence": 0.95,
        "suggested_event": "rejected",
        "rationale": "Declines the application.",
    }
)


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _use_gateway(payload: str) -> None:
    app.dependency_overrides[get_gateway] = lambda: LLMGateway(MockProvider(payload), max_retries=1)


def _setup(client: TestClient, classification: str = INTERVIEW_JSON) -> tuple[dict, str]:
    headers = _headers(client, USER_A)
    job = client.post("/api/v1/jobs", json={"url": DE_URL}, headers=headers).json()
    application = client.post(
        "/api/v1/applications", json={"job_id": job["id"]}, headers=headers
    ).json()
    integration = client.post(
        "/api/v1/integrations", json={"provider": "mock"}, headers=headers
    ).json()
    _use_gateway(classification)
    client.post(f"/api/v1/integrations/{integration['id']}/sync", headers=headers)
    return headers, str(application["id"])


def _queue(client: TestClient, headers: dict[str, str]) -> list[dict]:
    return client.get("/api/v1/emails?status=pending", headers=headers).json()


def _find(emails: list[dict], needle: str) -> dict:
    return next(email for email in emails if needle in email["subject"])


def test_emails_require_auth(client: TestClient) -> None:
    assert client.get("/api/v1/emails").status_code == 401


def test_review_queue_links_and_suggests(client: TestClient) -> None:
    headers, application_id = _setup(client)

    emails = _queue(client, headers)
    assert len(emails) == 3

    interview = _find(emails, "Interview")
    newsletter = _find(emails, "newsletter")
    assert interview["application_id"] == application_id
    assert newsletter["application_id"] is None

    suggestion = client.post(f"/api/v1/emails/{interview['id']}/suggest", headers=headers).json()
    assert suggestion["event_type"] == "interview"
    assert suggestion["application_id"] == application_id


def test_accept_interview_updates_application_and_calendar(client: TestClient) -> None:
    headers, application_id = _setup(client)
    interview = _find(_queue(client, headers), "Interview")

    accepted = client.post(f"/api/v1/emails/{interview['id']}/accept", headers=headers).json()
    assert accepted["status"] == "accepted"

    application = client.get(f"/api/v1/applications/{application_id}", headers=headers).json()
    assert application["status"] == "Interview"

    suggestions = client.get("/api/v1/calendar-suggestions", headers=headers).json()
    assert len(suggestions) == 1
    assert suggestions[0]["kind"] == "interview"


def test_accept_rejection_sets_application_closed(client: TestClient) -> None:
    headers, application_id = _setup(client, REJECTION_JSON)
    email = _find(_queue(client, headers), "application")
    client.post(f"/api/v1/emails/{email['id']}/accept", headers=headers)

    application = client.get(f"/api/v1/applications/{application_id}", headers=headers).json()
    assert application["status"] == "Rejected"


def test_accept_non_actionable_is_400(client: TestClient) -> None:
    headers, _ = _setup(client)
    newsletter = _find(_queue(client, headers), "newsletter")
    response = client.post(f"/api/v1/emails/{newsletter['id']}/accept", headers=headers)
    assert response.status_code == 400


def test_dismiss_removes_from_queue(client: TestClient) -> None:
    headers, _ = _setup(client)
    email = _find(_queue(client, headers), "newsletter")

    dismissed = client.post(f"/api/v1/emails/{email['id']}/dismiss", headers=headers).json()
    assert dismissed["status"] == "dismissed"
    assert all(item["id"] != email["id"] for item in _queue(client, headers))


def test_emails_are_isolated_per_user(client: TestClient) -> None:
    headers_a, _ = _setup(client)
    email = _queue(client, headers_a)[0]

    headers_b = _headers(client, USER_B)
    assert client.get(f"/api/v1/emails/{email['id']}", headers=headers_b).status_code == 404
