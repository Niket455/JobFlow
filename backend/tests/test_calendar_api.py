import uuid

from fastapi.testclient import TestClient

USER_A = {"email": "calendar-a@example.com", "password": "supersecret1"}
USER_B = {"email": "calendar-b@example.com", "password": "supersecret2"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _create(client: TestClient, headers: dict[str, str], **extra: object) -> dict:
    body = {"kind": "interview", "title": "Interview with Acme", **extra}
    response = client.post("/api/v1/calendar-suggestions", json=body, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_calendar_requires_auth(client: TestClient) -> None:
    assert client.post("/api/v1/calendar-suggestions", json={"title": "x"}).status_code == 401


def test_create_list_confirm(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    suggestion = _create(client, headers, proposed_at="2026-02-01T10:00:00Z")
    assert suggestion["status"] == "suggested"

    listed = client.get("/api/v1/calendar-suggestions", headers=headers).json()
    assert len(listed) == 1

    confirmed = client.post(
        f"/api/v1/calendar-suggestions/{suggestion['id']}/confirm", headers=headers
    ).json()
    assert confirmed["status"] == "confirmed"


def test_dismiss(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    suggestion = _create(client, headers)

    dismissed = client.post(
        f"/api/v1/calendar-suggestions/{suggestion['id']}/dismiss", headers=headers
    ).json()
    assert dismissed["status"] == "dismissed"


def test_calendar_confirm_unknown_is_404(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    response = client.post(f"/api/v1/calendar-suggestions/{UNKNOWN}/confirm", headers=headers)
    assert response.status_code == 404


def test_calendar_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    suggestion = _create(client, headers_a)

    headers_b = _headers(client, USER_B)
    assert client.get("/api/v1/calendar-suggestions", headers=headers_b).json() == []
    assert (
        client.post(
            f"/api/v1/calendar-suggestions/{uuid.UUID(suggestion['id'])}/confirm",
            headers=headers_b,
        ).status_code
        == 404
    )
