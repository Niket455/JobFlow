import json

from fake_fetcher import DE_URL
from fastapi.testclient import TestClient

from app.api.deps import get_gateway
from app.gateway.gateway import LLMGateway
from app.gateway.providers.mock_provider import MockProvider
from app.main import app

USER_A = {"email": "integrations-a@example.com", "password": "supersecret1"}
USER_B = {"email": "integrations-b@example.com", "password": "supersecret2"}

CLASSIFY_JSON = json.dumps(
    {
        "classification": "acknowledgement",
        "confidence": 0.8,
        "suggested_event": None,
        "rationale": "Acknowledges receipt.",
    }
)


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _use_gateway(payload: str) -> None:
    app.dependency_overrides[get_gateway] = lambda: LLMGateway(MockProvider(payload), max_retries=1)


def _connect(client: TestClient, headers: dict[str, str], provider: str = "mock") -> dict:
    response = client.post("/api/v1/integrations", json={"provider": provider}, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_integrations_require_auth(client: TestClient) -> None:
    assert client.post("/api/v1/integrations", json={"provider": "mock"}).status_code == 401


def test_connect_list_and_disconnect(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    integration = _connect(client, headers)
    assert integration["provider"] == "mock"
    assert integration["status"] == "connected"

    listed = client.get("/api/v1/integrations", headers=headers).json()
    assert len(listed) == 1

    assert (
        client.delete(f"/api/v1/integrations/{integration['id']}", headers=headers).status_code
        == 204
    )
    assert client.get("/api/v1/integrations", headers=headers).json() == []


def test_gmail_is_not_configured(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    response = client.post("/api/v1/integrations", json={"provider": "gmail"}, headers=headers)
    assert response.status_code == 400


def test_sync_is_idempotent(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    client.post("/api/v1/jobs", json={"url": DE_URL}, headers=headers)
    integration = _connect(client, headers)
    _use_gateway(CLASSIFY_JSON)

    first = client.post(f"/api/v1/integrations/{integration['id']}/sync", headers=headers).json()
    assert first == {"created": 3, "skipped": 0}

    second = client.post(f"/api/v1/integrations/{integration['id']}/sync", headers=headers).json()
    assert second == {"created": 0, "skipped": 3}


def test_emails_are_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    integration = _connect(client, headers_a)

    headers_b = _headers(client, USER_B)
    assert client.get("/api/v1/emails", headers=headers_b).json() == []
    assert (
        client.post(f"/api/v1/integrations/{integration['id']}/sync", headers=headers_b).status_code
        == 404
    )
