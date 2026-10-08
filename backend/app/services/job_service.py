import uuid

from app.models.company import Company
from app.models.job import Job
from app.models.job_source import JobSource
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.schemas.job import JobRead, JobSourceRead, JobSummary


class JobNotFoundError(Exception):
    pass


class JobService:
    def __init__(
        self,
        jobs: JobRepository,
        sources: JobSourceRepository,
        companies: CompanyRepository,
    ) -> None:
        self.jobs = jobs
        self.sources = sources
        self.companies = companies

    def list_for_user(self, user: User, *, limit: int, offset: int) -> list[JobSummary]:
        jobs = self.jobs.list_for_user(user.id, limit=limit, offset=offset)
        companies = self.companies.get_many({job.company_id for job in jobs if job.company_id})
        return [self._summary(job, companies) for job in jobs]

    def get(self, user: User, job_id: uuid.UUID) -> JobRead:
        job = self._visible_job(user, job_id)
        company = self.companies.get(job.company_id) if job.company_id is not None else None
        return self._to_read(job, company, self.sources.list_for_job(job.id))

    def list_sources(self, user: User, job_id: uuid.UUID) -> list[JobSourceRead]:
        self._visible_job(user, job_id)
        return [
            JobSourceRead.model_validate(source) for source in self.sources.list_for_job(job_id)
        ]

    def _visible_job(self, user: User, job_id: uuid.UUID) -> Job:
        job = self.jobs.get(job_id)
        if job is None or not self.sources.exists(job_id, user.id):
            raise JobNotFoundError
        return job

    @staticmethod
    def _summary(job: Job, companies: dict[uuid.UUID, Company]) -> JobSummary:
        company = companies.get(job.company_id) if job.company_id is not None else None
        return JobSummary(
            id=job.id,
            title=job.title,
            company=company.name if company is not None else None,
            location=job.location,
            status=job.status,
            possible_duplicate_of_id=job.possible_duplicate_of_id,
            first_seen_at=job.first_seen_at,
            last_seen_at=job.last_seen_at,
        )

    @staticmethod
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
