import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from app.models.application import Application
from app.models.application_event import ApplicationEvent
from app.models.job import Job
from app.services.application_status import StatusEvent, derive


@dataclass(frozen=True)
class TimelineEntry:
    application_id: uuid.UUID
    job_id: uuid.UUID
    title: str
    status: str
    days_since_update: int


def load_timeline(
    applications: list[Application],
    grouped_events: dict[uuid.UUID, list[ApplicationEvent]],
    titles: dict[uuid.UUID, Job],
    *,
    now: datetime,
) -> list[TimelineEntry]:
    """Derive each application's status, title, and days-since-update."""
    return [
        TimelineEntry(
            application_id=application.id,
            job_id=application.job_id,
            title=job_title(titles, application.job_id),
            status=_status(grouped_events.get(application.id, [])),
            days_since_update=days_since(application.updated_at, now),
        )
        for application in applications
    ]


def job_title(titles: dict[uuid.UUID, Job], job_id: uuid.UUID) -> str:
    job = titles.get(job_id)
    return job.title if job is not None else "this role"


def days_since(updated_at: datetime | None, now: datetime) -> int:
    if updated_at is None:
        return 0
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)
    return max(0, (now - updated_at).days)


def _status(events: list[ApplicationEvent]) -> str:
    status_events = [
        StatusEvent(type=event.type, occurred_at=event.occurred_at, created_at=event.created_at)
        for event in events
    ]
    return derive(status_events)[0]
