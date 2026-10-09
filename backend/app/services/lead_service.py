import uuid

from sqlalchemy.orm import Session

from app.adapters.base import Fetcher, FetchError, RobotsDisallowedError
from app.models.lead import Lead
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.fetch_log_repository import FetchLogRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.repositories.lead_repository import LeadRepository
from app.schemas.job import JobRead
from app.schemas.lead import LeadRead, LeadSummary
from app.services.job_ingestion_service import JobIngestionService
from app.services.job_service import JobService


class LeadNotFoundError(Exception):
    pass


class LeadService:
    """Lead lifecycle: list/get/dismiss, and capture (promote) into a canonical job."""

    def __init__(
        self,
        leads: LeadRepository,
        ingestion: JobIngestionService,
        jobs: JobService,
    ) -> None:
        self.leads = leads
        self.ingestion = ingestion
        self.jobs = jobs

    def list_for_user(
        self,
        user: User,
        *,
        status: str | None = None,
        limit: int,
        offset: int,
    ) -> list[LeadSummary]:
        leads = self.leads.list_for_user(user.id, status=status, limit=limit, offset=offset)
        return [LeadSummary.model_validate(lead) for lead in leads]

    def get(self, user: User, lead_id: uuid.UUID) -> LeadRead:
        return LeadRead.model_validate(self._visible(user, lead_id))

    def capture(self, user: User, lead_id: uuid.UUID) -> JobRead:
        lead = self._visible(user, lead_id)
        if lead.status == "Captured" and lead.job_id is not None:
            return self.jobs.get(user, lead.job_id)
        lead.status = "Queued"
        try:
            job = self.ingestion.ingest(user, lead.url)
        except (FetchError, RobotsDisallowedError):
            self.leads.commit()
            raise
        lead.status = "Captured"
        lead.job_id = job.id
        self.leads.commit()
        return job

    def dismiss(self, user: User, lead_id: uuid.UUID) -> LeadRead:
        lead = self._visible(user, lead_id)
        lead.status = "Dismissed"
        self.leads.commit()
        return LeadRead.model_validate(lead)

    def _visible(self, user: User, lead_id: uuid.UUID) -> Lead:
        lead = self.leads.get_for_user(user.id, lead_id)
        if lead is None:
            raise LeadNotFoundError
        return lead


def build_lead_service(db: Session, fetcher: Fetcher) -> LeadService:
    companies = CompanyRepository(db)
    jobs = JobRepository(db)
    sources = JobSourceRepository(db)
    return LeadService(
        LeadRepository(db),
        JobIngestionService(companies, jobs, sources, FetchLogRepository(db), fetcher),
        JobService(jobs, sources, companies),
    )
