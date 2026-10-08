from app.adapters.user_url import build_fetcher
from app.core.config import settings
from app.core.db import SessionLocal
from app.repositories.fetch_log_repository import FetchLogRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
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
