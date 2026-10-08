from datetime import UTC, datetime

from app.adapters.factory import build_fetcher
from app.core.config import settings
from app.core.db import SessionLocal
from app.email.factory import build_email_sender
from app.repositories.fetch_log_repository import FetchLogRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.services.alert_service import build_alert_service
from app.services.job_refresh_service import JobRefreshService
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.recheck_jobs")
def recheck_jobs() -> int:
    """Refresh every Active job whose next_check_at has passed. Returns jobs checked."""
    session = SessionLocal()
    try:
        service = JobRefreshService(
            JobRepository(session),
            JobSourceRepository(session),
            FetchLogRepository(session),
            build_fetcher(),
        )
        return service.refresh_due(limit=settings.recheck_batch_size)
    finally:
        session.close()


@celery_app.task(name="app.workers.tasks.run_alerts")
def run_alerts() -> int:
    """Run every due alert digest. Returns the number of alerts processed."""
    session = SessionLocal()
    try:
        service = build_alert_service(session, build_email_sender())
        return service.run_due(now=datetime.now(UTC), limit=settings.alerts_batch_size)
    finally:
        session.close()
