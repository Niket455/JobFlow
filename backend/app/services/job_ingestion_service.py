import uuid
from datetime import UTC, datetime, timedelta

from app.adapters.base import Fetcher, FetchError, RobotsDisallowedError
from app.core.config import settings
from app.models.company import Company
from app.models.job import Job
from app.models.job_source import JobSource
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.fetch_log_repository import FetchLogRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.schemas.job import JobRead, JobSourceRead
from app.services.dedupe import content_hash, normalized_company_name
from app.services.job_normalizer import normalize
from app.services.url_canonicalizer import canonicalize

DEFAULT_ADAPTER = "user_url"


class JobIngestionService:
    """Past-URL ingestion: fetch → normalize → dedupe into a canonical job → log the fetch."""

    def __init__(
        self,
        companies: CompanyRepository,
        jobs: JobRepository,
        sources: JobSourceRepository,
        fetch_logs: FetchLogRepository,
        fetcher: Fetcher,
    ) -> None:
        self.companies = companies
        self.jobs = jobs
        self.sources = sources
        self.fetch_logs = fetch_logs
        self.fetcher = fetcher

    def ingest(self, user: User, url: str) -> JobRead:
        try:
            result = self.fetcher.fetch(url)
        except (FetchError, RobotsDisallowedError) as exc:
            self.fetch_logs.create(
                adapter=DEFAULT_ADAPTER,
                url=url,
                user_id=user.id,
                status_code=None,
                ok=False,
                error=str(exc),
            )
            self.jobs.commit()
            raise

        normalized = normalize(result)
        final_url = canonicalize(result.url)
        job_hash = content_hash(normalized.title, normalized.company_name, normalized.location)
        now = datetime.now(UTC)
        etag = result.headers.get("etag")

        existing_source = self.sources.get_for_url_and_user(final_url, user.id)
        job = self.jobs.get(existing_source.job_id) if existing_source is not None else None
        if job is None:
            job = self.jobs.find_by_content_hash(job_hash)

        if job is None:
            company = self._company_for(normalized.company_name)
            job = self.jobs.create(
                company_id=company.id if company is not None else None,
                title=normalized.title,
                location=normalized.location,
                description=normalized.description,
                status=_status_for(normalized.valid_through),
                content_hash=job_hash,
                possible_duplicate_of_id=self._possible_duplicate(company, normalized.title),
                first_seen_at=now,
                last_seen_at=now,
                next_check_at=now + timedelta(hours=settings.job_recheck_hours),
            )
        else:
            job.last_seen_at = now
            job.status = "Active"
            job.next_check_at = now + timedelta(hours=settings.job_recheck_hours)

        if existing_source is not None:
            existing_source.last_seen_at = now
        else:
            self.sources.create(
                job_id=job.id,
                added_by_user_id=user.id,
                adapter=result.adapter,
                url=url,
                canonical_url=final_url,
                external_id=normalized.external_id,
                etag=etag,
                content_hash=job_hash,
                raw=normalized.raw,
                first_seen_at=now,
                last_seen_at=now,
            )

        self.fetch_logs.create(
            adapter=result.adapter,
            url=url,
            user_id=user.id,
            status_code=result.status_code,
            ok=True,
            error=None,
            etag=etag,
            content_hash=job_hash,
        )
        self.jobs.commit()

        company = self.companies.get(job.company_id) if job.company_id is not None else None
        return _to_read(job, company, self.sources.list_for_job(job.id))

    def _company_for(self, name: str | None) -> Company | None:
        if not name:
            return None
        return self.companies.get_or_create(name, normalized_company_name(name))

    def _possible_duplicate(self, company: Company | None, title: str) -> uuid.UUID | None:
        if company is None:
            return None
        candidate = self.jobs.find_by_company_and_title(company.id, title)
        return candidate.id if candidate is not None else None


def _status_for(valid_through: str | None) -> str:
    parsed = _parse_datetime(valid_through)
    if parsed is None:
        return "Active"
    return "Expired" if parsed < datetime.now(UTC) else "Active"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _to_read(job: Job, company: Company | None, sources: list[JobSource]) -> JobRead:
    return JobRead(
        id=job.id,
        title=job.title,
        company=company.name if company is not None else None,
        location=job.location,
        status=job.status,
        possible_duplicate_of_id=job.possible_duplicate_of_id,
        first_seen_at=job.first_seen_at,
        last_seen_at=job.last_seen_at,
        description=job.description,
        sources=[JobSourceRead.model_validate(source) for source in sources],
    )
