import uuid
from datetime import UTC, datetime, timedelta

from fake_fetcher import DE_URL, FakeFetcher
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.fetch_log import FetchLog
from app.models.job import Job
from app.repositories.fetch_log_repository import FetchLogRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.services.job_refresh_service import JobRefreshService

USER_A = {"email": "refresh-a@example.com", "password": "supersecret1"}
UNKNOWN = "00000000-0000-0000-0000-000000000000"


def _headers(client: TestClient, credentials: dict[str, str]) -> dict[str, str]:
    client.post("/api/v1/auth/register", json=credentials)
    tokens = client.post("/api/v1/auth/login", json=credentials).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _ingest(client: TestClient, headers: dict[str, str], url: str) -> dict[str, object]:
    return client.post("/api/v1/jobs", json={"url": url}, headers=headers).json()


def test_refresh_requires_auth(client: TestClient) -> None:
    assert client.post(f"/api/v1/jobs/{UNKNOWN}/refresh").status_code == 401


def test_refresh_unknown_job_returns_404(client: TestClient) -> None:
    headers = _headers(client, USER_A)
    assert client.post(f"/api/v1/jobs/{UNKNOWN}/refresh", headers=headers).status_code == 404


def test_refresh_stays_active_on_success(client: TestClient, db_session: Session) -> None:
    headers = _headers(client, USER_A)
    job = _ingest(client, headers, DE_URL)

    response = client.post(f"/api/v1/jobs/{job['id']}/refresh", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "Active"
    assert db_session.scalar(select(func.count()).select_from(FetchLog)) == 2


def test_refresh_marks_expired_on_404(client: TestClient, fake_fetcher: FakeFetcher) -> None:
    headers = _headers(client, USER_A)
    job = _ingest(client, headers, DE_URL)
    assert job["status"] == "Active"

    fake_fetcher.pages.pop(DE_URL)
    response = client.post(f"/api/v1/jobs/{job['id']}/refresh", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "Expired"


def test_refresh_keeps_status_on_robots_denied(
    client: TestClient, fake_fetcher: FakeFetcher
) -> None:
    headers = _headers(client, USER_A)
    job = _ingest(client, headers, DE_URL)

    fake_fetcher.blocked.add(DE_URL)
    response = client.post(f"/api/v1/jobs/{job['id']}/refresh", headers=headers)

    assert response.status_code == 200
    assert response.json()["status"] == "Active"


def test_refresh_due_expires_stale_job(
    client: TestClient, db_session: Session, fake_fetcher: FakeFetcher
) -> None:
    headers = _headers(client, USER_A)
    job = _ingest(client, headers, DE_URL)

    row = db_session.get(Job, uuid.UUID(str(job["id"])))
    assert row is not None
    row.next_check_at = datetime.now(UTC) - timedelta(hours=1)
    db_session.commit()
    fake_fetcher.pages.pop(DE_URL)

    service = JobRefreshService(
        JobRepository(db_session),
        JobSourceRepository(db_session),
        FetchLogRepository(db_session),
        fake_fetcher,
    )
    assert service.refresh_due(limit=10) == 1
    assert row.status == "Expired"
    assert row.last_checked_at is not None


def test_recheck_task_is_registered() -> None:
    from app.workers.tasks import recheck_jobs

    assert recheck_jobs.name == "app.workers.tasks.recheck_jobs"
