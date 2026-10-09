import httpx
import pytest
from fake_fetcher import ASHBY_URL, GH_URL, LEVER_URL, SR_URL, ats_client
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.factory import build_fetcher
from app.api.deps import get_fetcher
from app.main import app
from app.models.job_source import JobSource

USER_A = {"email": "ats-a@example.com", "password": "supersecret1"}


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _use_ats_fetcher() -> None:
    client: httpx.Client = ats_client()
    app.dependency_overrides[get_fetcher] = lambda: build_fetcher(client)


def _ingest(client: TestClient, headers: dict[str, str], url: str):
    return client.post("/api/v1/jobs", json={"url": url}, headers=headers)


@pytest.mark.parametrize(
    ("url", "adapter", "title"),
    [
        (GH_URL, "greenhouse", "Vault Designer"),
        (LEVER_URL, "lever", "Backend Engineer"),
        (ASHBY_URL, "ashby", "Product Manager"),
        (SR_URL, "smartrecruiters", "SEO Manager"),
    ],
)
def test_ats_ingest_records_adapter(
    client: TestClient, db_session: Session, url: str, adapter: str, title: str
) -> None:
    _use_ats_fetcher()
    headers = _headers(client, USER_A)

    response = _ingest(client, headers, url)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == title
    assert body["sources"][0]["adapter"] == adapter

    row = db_session.scalar(select(JobSource).where(JobSource.adapter == adapter))
    assert row is not None


def test_ats_reingest_dedupes(client: TestClient) -> None:
    _use_ats_fetcher()
    headers = _headers(client, USER_A)

    first = _ingest(client, headers, GH_URL).json()
    second = _ingest(client, headers, GH_URL).json()

    assert second["id"] == first["id"]
    assert len(second["sources"]) == 1
    assert len(client.get("/api/v1/jobs", headers=headers).json()) == 1
