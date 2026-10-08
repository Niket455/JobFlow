import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.email.recording import RecordingEmailSender

USER = {"email": "notify@example.com", "password": "supersecret1"}


def _headers(client: TestClient) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=USER)
    tokens = client.post("/api/v1/auth/login", json=USER).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_requires_auth(client: TestClient) -> None:
    assert client.post("/api/v1/notifications/test").status_code == 401


def test_sends_test_email(client: TestClient, recording_email: RecordingEmailSender) -> None:
    headers = _headers(client)

    response = client.post("/api/v1/notifications/test", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["sent"] is True
    assert body["to"] == USER["email"]
    assert body["provider"] == "recording"
    assert len(recording_email.outbox) == 1
    assert recording_email.outbox[0].to == USER["email"]


def test_disabled_returns_503(
    client: TestClient,
    recording_email: RecordingEmailSender,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = _headers(client)
    monkeypatch.setattr(settings, "email_enabled", False)

    response = client.post("/api/v1/notifications/test", headers=headers)

    assert response.status_code == 503
    assert recording_email.outbox == []
