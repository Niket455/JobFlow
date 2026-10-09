from datetime import datetime

from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationRead
from app.services.application_service import ApplicationService
from app.services.job_ingestion_service import JobIngestionService


class CaptureService:
    """Bookmarklet/paste-URL capture: ingest the URL into a job and start an application."""

    def __init__(self, ingestion: JobIngestionService, applications: ApplicationService) -> None:
        self.ingestion = ingestion
        self.applications = applications

    def capture(
        self,
        user: User,
        *,
        url: str,
        applied_at: datetime | None,
        source: str | None,
    ) -> tuple[ApplicationRead, bool]:
        job = self.ingestion.ingest(user, url)
        payload = ApplicationCreate(job_id=job.id, applied_at=applied_at, source=source)
        return self.applications.ensure(user, payload)
