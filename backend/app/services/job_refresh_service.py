import uuid
from datetime import UTC, datetime, timedelta

from app.adapters.base import Fetcher, FetchError, RobotsDisallowedError
from app.core.config import settings
from app.models.job import Job
from app.models.user import User
from app.repositories.fetch_log_repository import FetchLogRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository

ADAPTER = "user_url"
EXPIRED_STATUS_CODES = {404, 410}


class JobRefreshService:
    """Lifecycle re-check: re-fetch a job's source and update Active/Expired/Unknown."""

    def __init__(
        self,
        jobs: JobRepository,
        sources: JobSourceRepository,
        fetch_logs: FetchLogRepository,
        fetcher: Fetcher,
    ) -> None:
        self.jobs = jobs
        self.sources = sources
        self.fetch_logs = fetch_logs
        self.fetcher = fetcher

    def refresh(self, user: User, job_id: uuid.UUID) -> Job | None:
        if not self.sources.exists(job_id, user.id):
            return None
        job = self.jobs.get(job_id)
        if job is None:
            return None
        self._recheck(job)
        return job

    def refresh_due(self, *, limit: int) -> int:
        due = self.jobs.list_due_for_recheck(datetime.now(UTC), limit=limit)
        for job in due:
            self._recheck(job)
        return len(due)

    def _recheck(self, job: Job) -> None:
        now = datetime.now(UTC)
        job.last_checked_at = now
        job.next_check_at = now + timedelta(hours=settings.job_recheck_hours)

        source = self.sources.latest_for_job(job.id)
        if source is None:
            self.jobs.commit()
            return

        try:
            result = self.fetcher.fetch(source.url)
        except RobotsDisallowedError as exc:
            self._log(source.url, status_code=None, ok=False, error=str(exc))
        except FetchError as exc:
            self._log(source.url, status_code=exc.status_code, ok=False, error=str(exc))
            job.status = "Expired" if exc.status_code in EXPIRED_STATUS_CODES else "Unknown"
        else:
            self._log(source.url, status_code=result.status_code, ok=True, error=None)
            job.status = "Active"
            job.last_seen_at = now
            source.last_seen_at = now
        self.jobs.commit()

    def _log(self, url: str, *, status_code: int | None, ok: bool, error: str | None) -> None:
        self.fetch_logs.create(
            adapter=ADAPTER,
            url=url,
            user_id=None,
            status_code=status_code,
            ok=ok,
            error=error,
            etag=None,
            content_hash=None,
        )
