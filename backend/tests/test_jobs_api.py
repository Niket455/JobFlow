from fake_fetcher import BLOCKED_URL, DE_URL, DOWN_URL, HTML_URL, MIRROR_URL, REMOTE_URL
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.fetch_log import FetchLog

USER_A = {"email": "jobs-a@example.com", "password": "supersecret1"}
USER_B = {"email": "jobs-b@example.com", "password": "supersecret2"}


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _ingest(client: TestClient, headers: dict[str, str], url: str):
    return client.post("/api/v1/jobs", json={"url": url}, headers=headers)


def test_ingest_requires_auth(client: TestClient) -> None:
    assert client.post("/api/v1/jobs", json={"url": DE_URL}).status_code == 401


def test_ingest_creates_job_source_and_fetch_log(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    response = _ingest(client, headers, DE_URL)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Data Engineer"
    assert body["company"] == "Acme Inc"
    assert body["location"] == "Bengaluru"
    assert body["status"] == "Active"
    assert body["possible_duplicate_of_id"] is None
    assert len(body["sources"]) == 1
    assert body["sources"][0]["adapter"] == "user_url"

    assert db_session.scalar(select(func.count()).select_from(FetchLog)) == 1


def test_reingest_same_url_dedupes(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    first = _ingest(client, headers, DE_URL).json()
    second = _ingest(client, headers, DE_URL).json()

    assert second["id"] == first["id"]
    assert len(second["sources"]) == 1
    assert len(client.get("/api/v1/jobs", headers=headers).json()) == 1


def test_cross_source_dedupe_links_two_sources(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    first = _ingest(client, headers, DE_URL).json()
    second = _ingest(client, headers, MIRROR_URL).json()

    assert second["id"] == first["id"]
    assert len(second["sources"]) == 2
    assert len(client.get("/api/v1/jobs", headers=headers).json()) == 1


def test_near_match_flags_possible_duplicate(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    first = _ingest(client, headers, DE_URL).json()
    duplicate = _ingest(client, headers, REMOTE_URL).json()

    assert duplicate["id"] != first["id"]
    assert duplicate["possible_duplicate_of_id"] == first["id"]
    assert len(client.get("/api/v1/jobs", headers=headers).json()) == 2


def test_jobs_are_isolated_per_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    _ingest(client, headers_a, DE_URL)

    headers_b = _headers(client, USER_B)
    assert client.get("/api/v1/jobs", headers=headers_b).json() == []


def test_cross_user_shares_canonical_job(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    job = _ingest(client, headers_a, DE_URL).json()

    headers_b = _headers(client, USER_B)
    b_job = _ingest(client, headers_b, DE_URL).json()

    assert b_job["id"] == job["id"]
    assert len(client.get("/api/v1/jobs", headers=headers_b).json()) == 1


def test_get_job_and_sources_scoped_to_user(client: TestClient) -> None:
    headers_a = _headers(client, USER_A)
    job = _ingest(client, headers_a, DE_URL).json()

    assert client.get(f"/api/v1/jobs/{job['id']}", headers=headers_a).status_code == 200
    assert client.get(f"/api/v1/jobs/{job['id']}/sources", headers=headers_a).status_code == 200

    headers_b = _headers(client, USER_B)
    assert client.get(f"/api/v1/jobs/{job['id']}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/jobs/{job['id']}/sources", headers=headers_b).status_code == 404


def test_robots_denied_returns_403(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    assert _ingest(client, headers, BLOCKED_URL).status_code == 403


def test_fetch_failure_returns_502(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    assert _ingest(client, headers, DOWN_URL).status_code == 502


def test_html_fallback_page_ingests(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    response = _ingest(client, headers, HTML_URL)
    assert response.status_code == 201
    assert response.json()["title"] == "Backend Engineer"
