from fake_fetcher import DE_URL, RSS_FEED_URL, FakeRedis, discovery_client
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.factory import DiscoveryRuntime
from app.adapters.robots import RobotsCache
from app.api.deps import get_discovery_runtime
from app.core.redis_cache import DailyQuota, RedisCache
from app.main import app
from app.models.job_source import JobSource

USER_A = {"email": "leads-a@example.com", "password": "supersecret1"}
USER_B = {"email": "leads-b@example.com", "password": "supersecret2"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _use_discovery_runtime() -> None:
    mock_client, _ = discovery_client()
    runtime = DiscoveryRuntime(
        client=mock_client,
        robots=RobotsCache(mock_client, ttl_seconds=3600),
        cache=RedisCache(FakeRedis()),
        quota=DailyQuota(FakeRedis()),
    )
    app.dependency_overrides[get_discovery_runtime] = lambda: runtime


def _create_source(
    client: TestClient,
    headers: dict[str, str],
    *,
    kind: str = "rss",
    target: str = RSS_FEED_URL,
    label: str = "Feed",
) -> dict:
    response = client.post(
        "/api/v1/discovery-sources",
        json={"kind": kind, "label": label, "target": target},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _seed(client: TestClient, headers: dict[str, str]) -> dict:
    source = _create_source(client, headers)
    run = client.post(f"/api/v1/discovery-sources/{source['id']}/run", headers=headers)
    assert run.status_code == 200, run.text
    return run.json()


def test_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/leads").status_code == 401
    assert (
        client.post(
            "/api/v1/discovery-sources",
            json={"kind": "rss", "label": "x", "target": "y"},
        ).status_code
        == 401
    )
    assert client.get("/api/v1/discovery-sources").status_code == 401
    assert client.post(f"/api/v1/leads/{UNKNOWN}/capture").status_code == 401


def test_create_run_and_list_leads(client: TestClient) -> None:
    _use_discovery_runtime()
    headers = _headers(client, USER_A)
    assert _seed(client, headers) == {"created": 2, "existing": 0}

    leads = client.get("/api/v1/leads", headers=headers).json()
    assert len(leads) == 2
    assert {lead["status"] for lead in leads} == {"New"}
    assert {lead["domain"] for lead in leads} == {"jobs.example.com"}
    assert len(client.get("/api/v1/leads?status=New", headers=headers).json()) == 2
    assert client.get("/api/v1/leads?status=Dismissed", headers=headers).json() == []

    source = client.get("/api/v1/discovery-sources", headers=headers).json()[0]
    assert source["last_status"] == "ok"


def test_run_is_idempotent(client: TestClient) -> None:
    _use_discovery_runtime()
    headers = _headers(client, USER_A)
    source = _create_source(client, headers)
    first = client.post(f"/api/v1/discovery-sources/{source['id']}/run", headers=headers).json()
    second = client.post(f"/api/v1/discovery-sources/{source['id']}/run", headers=headers).json()
    assert first == {"created": 2, "existing": 0}
    assert second == {"created": 0, "existing": 2}


def test_unknown_kind_is_rejected(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    response = client.post(
        "/api/v1/discovery-sources",
        json={"kind": "chat", "label": "x", "target": "y"},
        headers=headers,
    )
    assert response.status_code == 400


def test_google_pse_disabled_by_default(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    response = client.post(
        "/api/v1/discovery-sources",
        json={"kind": "google_pse", "label": "x", "target": "python jobs"},
        headers=headers,
    )
    assert response.status_code == 403


def test_leads_are_isolated_per_user(client: TestClient) -> None:
    _use_discovery_runtime()
    headers_a = _headers(client, USER_A)
    _seed(client, headers_a)
    lead_id = client.get("/api/v1/leads", headers=headers_a).json()[0]["id"]

    headers_b = _headers(client, USER_B)
    assert client.get("/api/v1/leads", headers=headers_b).json() == []
    assert client.get(f"/api/v1/leads/{lead_id}", headers=headers_b).status_code == 404
    assert client.post(f"/api/v1/leads/{lead_id}/capture", headers=headers_b).status_code == 404


def test_capture_promotes_lead_to_job(client: TestClient, db_session: Session) -> None:
    _use_discovery_runtime()
    headers = _headers(client, USER_A)
    _seed(client, headers)
    leads = client.get("/api/v1/leads", headers=headers).json()
    lead = next(lead for lead in leads if lead["url"] == DE_URL)

    response = client.post(f"/api/v1/leads/{lead['id']}/capture", headers=headers)
    assert response.status_code == 201, response.text
    assert response.json()["title"] == "Data Engineer"

    updated = client.get(f"/api/v1/leads/{lead['id']}", headers=headers).json()
    assert updated["status"] == "Captured"
    assert updated["job_id"] == response.json()["id"]
    assert db_session.scalar(select(JobSource).where(JobSource.adapter == "user_url")) is not None


def test_capture_fetch_failure_leaves_lead_queued(client: TestClient) -> None:
    _use_discovery_runtime()
    headers = _headers(client, USER_A)
    _seed(client, headers)
    leads = client.get("/api/v1/leads", headers=headers).json()
    ghost = next(lead for lead in leads if lead["url"].endswith("ghost-role"))

    assert client.post(f"/api/v1/leads/{ghost['id']}/capture", headers=headers).status_code == 502
    updated = client.get(f"/api/v1/leads/{ghost['id']}", headers=headers).json()
    assert updated["status"] == "Queued"


def test_dismiss_and_delete_source(client: TestClient) -> None:
    _use_discovery_runtime()
    headers = _headers(client, USER_A)
    source = _create_source(client, headers)
    client.post(f"/api/v1/discovery-sources/{source['id']}/run", headers=headers)
    lead_id = client.get("/api/v1/leads", headers=headers).json()[0]["id"]

    dismissed = client.post(f"/api/v1/leads/{lead_id}/dismiss", headers=headers).json()
    assert dismissed["status"] == "Dismissed"
    assert len(client.get("/api/v1/leads?status=Dismissed", headers=headers).json()) == 1

    assert (
        client.delete(f"/api/v1/discovery-sources/{source['id']}", headers=headers).status_code
        == 204
    )
    assert client.get("/api/v1/discovery-sources", headers=headers).json() == []


def test_discover_task_is_registered() -> None:
    from app.workers.tasks import discover_leads

    assert discover_leads.name == "app.workers.tasks.discover_leads"
