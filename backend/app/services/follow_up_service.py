from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.repositories.application_event_repository import ApplicationEventRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_repository import JobRepository
from app.schemas.crm import FollowUpItem, FollowUpList
from app.services.application_timeline import TimelineEntry, load_timeline


class FollowUpService:
    """Deterministic CRM follow-up view over the user's applications."""

    def __init__(
        self,
        applications: ApplicationRepository,
        events: ApplicationEventRepository,
        jobs: JobRepository,
    ) -> None:
        self.applications = applications
        self.events = events
        self.jobs = jobs

    def list_for_user(self, user: User, *, now: datetime) -> FollowUpList:
        applications = self.applications.list_all_for_user(user.id)
        grouped = self.events.list_for_applications(
            [application.id for application in applications]
        )
        titles = self.jobs.get_many({application.job_id for application in applications})
        timeline = load_timeline(applications, grouped, titles, now=now)

        items: list[FollowUpItem] = []
        for entry in timeline:
            if (
                entry.status == "Applied"
                and entry.days_since_update >= settings.daily_plan_follow_up_days
            ):
                items.append(_item(entry, "Follow up"))
            elif entry.status == "Interview":
                items.append(_item(entry, "Prepare"))
        items.sort(key=lambda item: item.days_since_update, reverse=True)

        return FollowUpList(
            items=items,
            generated_from={"applications": len(applications), "follow_ups": len(items)},
        )


def build_follow_up_service(db: Session) -> FollowUpService:
    return FollowUpService(
        ApplicationRepository(db),
        ApplicationEventRepository(db),
        JobRepository(db),
    )


def _item(entry: TimelineEntry, action: str) -> FollowUpItem:
    return FollowUpItem(
        application_id=entry.application_id,
        job_id=entry.job_id,
        title=entry.title,
        status=entry.status,
        days_since_update=entry.days_since_update,
        action=action,
    )
