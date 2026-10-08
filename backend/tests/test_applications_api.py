from fake_fetcher import DE_URL, REMOTE_URL
from fastapi.testclient import TestClient

USER_A = {"email": "apps-a@example.com", "password": "supersecret1"}
USER_B = {"email": "apps-b@example.com", "password": "supersecret2"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _ingest(client: TestClient, headers: dict[str, str], url: str) -> dict[str, object]:
    return client.post("/api/v1/jobs", json={"url": url}, headers=headers).json()


def test_create_requires_auth(client: TestClient) -> None:
    assert client.post("/api/v1/applications", json={"job_id": UNKNOWN}).status_code == 401


def test_create_defaults_to_saved(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    job = _ingest(client, headers, DE_URL)

    response = client.post("/api/v1/applications", json={"job_id": job["id"]}, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "Saved"
    assert body["kanban"] == "Saved"
    assert [event["type"] for event in body["events"]] == ["saved"]


def test_create_with_applied_at_is_applied(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    job = _ingest(client, headers, DE_URL)

    response = client.post(
        "/api/v1/applications",
        json={"job_id": job["id"], "applied_at": "2026-01-02T00:00:00Z"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "Applied"


def test_duplicate_application_returns_409(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    job = _ingest(client, headers, DE_URL)
    first = client.post("/api/v1/applications", json={"job_id": job["id"]}, headers=headers).json()

    second = client.post("/api/v1/applications", json={"job_id": job["id"]}, headers=headers)
    assert second.status_code == 409
    assert second.json()["detail"]["application_id"] == first["id"]


def test_unknown_or_foreign_job_returns_404(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    job = _ingest(client, headers_a, DE_URL)

    unknown = client.post("/api/v1/applications", json={"job_id": UNKNOWN}, headers=headers_a)
    assert unknown.status_code == 404

    headers_b = _headers(client, USER_B)
    foreign = client.post("/api/v1/applications", json={"job_id": job["id"]}, headers=headers_b)
    assert foreign.status_code == 404


def test_events_advance_derived_status(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    job = _ingest(client, headers, DE_URL)
    application = client.post(
        "/api/v1/applications", json={"job_id": job["id"]}, headers=headers
    ).json()

    interviewed = client.post(
        f"/api/v1/applications/{application['id']}/events",
        json={"type": "interview"},
        headers=headers,
    )
    assert interviewed.status_code == 201
    assert interviewed.json()["status"] == "Interview"
    assert interviewed.json()["kanban"] == "Interview"

    rejected = client.post(
        f"/api/v1/applications/{application['id']}/events",
        json={"type": "rejected", "payload": {"reason": "no response"}},
        headers=headers,
    )
    assert rejected.json()["status"] == "Rejected"
    assert rejected.json()["kanban"] == "Closed"

    events = client.get(f"/api/v1/applications/{application['id']}/events", headers=headers).json()
    assert [event["type"] for event in events] == ["saved", "interview", "rejected"]


def test_list_and_get_are_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    job = _ingest(client, headers_a, DE_URL)
    other = _ingest(client, headers_a, REMOTE_URL)
    client.post("/api/v1/applications", json={"job_id": job["id"]}, headers=headers_a)
    client.post("/api/v1/applications", json={"job_id": other["id"]}, headers=headers_a)

    listing = client.get("/api/v1/applications", headers=headers_a).json()
    assert len(listing) == 2
    detail = client.get(f"/api/v1/applications/{listing[0]['id']}", headers=headers_a)
    assert detail.status_code == 200

    headers_b = _headers(client, USER_B)
    assert client.get("/api/v1/applications", headers=headers_b).json() == []
    assert (
        client.get(f"/api/v1/applications/{listing[0]['id']}", headers=headers_b).status_code == 404
    )
