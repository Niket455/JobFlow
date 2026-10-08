import uuid
from datetime import UTC, datetime

from app.models.application import Application
from app.models.application_event import ApplicationEvent
from app.models.user import User
from app.repositories.application_event_repository import ApplicationEventRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.schemas.application import (
    ApplicationCreate,
    ApplicationEventCreate,
    ApplicationEventRead,
    ApplicationRead,
    ApplicationSummary,
)
from app.services.application_status import StatusEvent, derive
from app.services.job_service import JobNotFoundError


class ApplicationNotFoundError(Exception):
    pass


class DuplicateApplicationError(Exception):
    def __init__(self, application_id: uuid.UUID) -> None:
        super().__init__("An application already exists for this job")
        self.application_id = application_id


class ApplicationService:
    """Event-sourced application tracker: status/kanban are always derived from the event log."""

    def __init__(
        self,
        applications: ApplicationRepository,
        events: ApplicationEventRepository,
        jobs: JobRepository,
        sources: JobSourceRepository,
    ) -> None:
        self.applications = applications
        self.events = events
        self.jobs = jobs
        self.sources = sources

    def create(self, user: User, payload: ApplicationCreate) -> ApplicationRead:
        job = self.jobs.get(payload.job_id)
        if job is None or not self.sources.exists(payload.job_id, user.id):
            raise JobNotFoundError
        existing = self.applications.get_for_user_job(user.id, payload.job_id)
        if existing is not None:
            raise DuplicateApplicationError(existing.id)

        now = datetime.now(UTC)
        application = self.applications.create(
            user_id=user.id,
            job_id=payload.job_id,
            resume_version_id=payload.resume_version_id,
            source=payload.source,
            applied_at=payload.applied_at,
        )
        self.events.create(
            application_id=application.id,
            type="applied" if payload.applied_at is not None else "saved",
            payload={},
            occurred_at=payload.applied_at or now,
        )
        self.applications.commit()
        return self._to_read(application)

    def add_event(
        self, user: User, application_id: uuid.UUID, payload: ApplicationEventCreate
    ) -> ApplicationRead:
        application = self._get(user, application_id)
        occurred = payload.occurred_at or datetime.now(UTC)
        self.events.create(
            application_id=application.id,
            type=payload.type,
            payload=payload.payload,
            occurred_at=occurred,
        )
        if payload.type.strip().lower() == "applied" and application.applied_at is None:
            application.applied_at = occurred
        application.updated_at = datetime.now(UTC)
        self.applications.commit()
        return self._to_read(application)

    def list_for_user(self, user: User, *, limit: int, offset: int) -> list[ApplicationSummary]:
        applications = self.applications.list_for_user(user.id, limit=limit, offset=offset)
        grouped = self.events.list_for_applications(
            [application.id for application in applications]
        )
        return [
            self._summary(application, grouped.get(application.id, []))
            for application in applications
        ]

    def get(self, user: User, application_id: uuid.UUID) -> ApplicationRead:
        return self._to_read(self._get(user, application_id))

    def list_events(self, user: User, application_id: uuid.UUID) -> list[ApplicationEventRead]:
        application = self._get(user, application_id)
        return [
            ApplicationEventRead.model_validate(event)
            for event in self.events.list_for_application(application.id)
        ]

    def _get(self, user: User, application_id: uuid.UUID) -> Application:
        application = self.applications.get_for_user(user.id, application_id)
        if application is None:
            raise ApplicationNotFoundError
        return application

    def _summary(
        self, application: Application, events: list[ApplicationEvent]
    ) -> ApplicationSummary:
        status, kanban = derive(_status_events(events))
        return ApplicationSummary(
            id=application.id,
            job_id=application.job_id,
            status=status,
            kanban=kanban,
            applied_at=application.applied_at,
            resume_version_id=application.resume_version_id,
            source=application.source,
            updated_at=application.updated_at,
        )

    def _to_read(self, application: Application) -> ApplicationRead:
        events = self.events.list_for_application(application.id)
        status, kanban = derive(_status_events(events))
        return ApplicationRead(
            id=application.id,
            job_id=application.job_id,
            status=status,
            kanban=kanban,
            applied_at=application.applied_at,
            resume_version_id=application.resume_version_id,
            source=application.source,
            updated_at=application.updated_at,
            events=[ApplicationEventRead.model_validate(event) for event in events],
        )


def _status_events(events: list[ApplicationEvent]) -> list[StatusEvent]:
    return [
        StatusEvent(type=event.type, occurred_at=event.occurred_at, created_at=event.created_at)
        for event in events
    ]
