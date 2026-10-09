import uuid
from datetime import UTC, datetime

from fake_fetcher import RSS_FEED_URL
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.adapters.discovery import DiscoveredLead
from app.models.discovery_source import DiscoverySource
from app.models.user import User
from app.services.discovery_service import build_discovery_service

USER_A = {"email": "discovery-a@example.com", "password": "supersecret1"}


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


class _StubSource:
    def __init__(self, leads: list[DiscoveredLead]) -> None:
        self._leads = leads

    def discover(self, target: str) -> list[DiscoveredLead]:
        return list(self._leads)


def _create_source(client: TestClient, headers: dict[str, str], target: str) -> str:
    response = client.post(
        "/api/v1/discovery-sources",
        json={"kind": "rss", "label": "Feed", "target": target},
        headers=headers,
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def test_run_source_creates_leads_then_dedupes(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    source_id = _create_source(client, headers, RSS_FEED_URL)
    source = db_session.get(DiscoverySource, uuid.UUID(source_id))
    assert source is not None
    user = db_session.get(User, source.user_id)
    assert user is not None

    leads = [
        DiscoveredLead("A", "https://jobs.example.com/a", "jobs.example.com", "rss"),
        DiscoveredLead("B", "https://jobs.example.com/b", "jobs.example.com", "rss"),
    ]
    service = build_discovery_service(db_session, source_factory=lambda kind: _StubSource(leads))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    first = service.run_source(user, source.id, now=now)
    assert (first.created, first.existing) == (2, 0)
    second = service.run_source(user, source.id, now=now)
    assert (second.created, second.existing) == (0, 2)
    assert source.last_status == "ok"
    assert source.last_run_at == now


def test_run_due_skips_fresh_sources(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    fresh_id = _create_source(client, headers, "https://feeds.example.com/fresh.rss")
    stale_id = _create_source(client, headers, "https://feeds.example.com/stale.rss")
    fresh = db_session.get(DiscoverySource, uuid.UUID(fresh_id))
    stale = db_session.get(DiscoverySource, uuid.UUID(stale_id))
    assert fresh is not None and stale is not None
    now = datetime(2026, 1, 1, tzinfo=UTC)
    fresh.last_run_at = now
    db_session.commit()

    service = build_discovery_service(
        db_session,
        source_factory=lambda kind: _StubSource(
            [DiscoveredLead("X", "https://jobs.example.com/x", "jobs.example.com", "rss")]
        ),
    )
    assert service.run_due(now=now, limit=10) == 1
    assert stale.last_status == "ok"
    assert fresh.last_status is None
