import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.follow_up_state import FollowUpState
from app.models.user import User
from app.repositories.application_event_repository import ApplicationEventRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.follow_up_state_repository import FollowUpStateRepository
from app.repositories.job_repository import JobRepository
from app.schemas.crm import FollowUpItem, FollowUpList, FollowUpStateRead
from app.services.application_timeline import TimelineEntry, days_since, load_timeline


class FollowUpNotFoundError(Exception):
    pass


class FollowUpService:
    """Deterministic CRM follow-up view, honoring per-application snooze / followed-up state."""

    def __init__(
        self,
        applications: ApplicationRepository,
        events: ApplicationEventRepository,
        jobs: JobRepository,
        states: FollowUpStateRepository,
    ) -> None:
        self.applications = applications
        self.events = events
        self.jobs = jobs
        self.states = states

    def list_for_user(self, user: User, *, now: datetime) -> FollowUpList:
        applications = self.applications.list_all_for_user(user.id)
        grouped = self.events.list_for_applications(
            [application.id for application in applications]
        )
        titles = self.jobs.get_many({application.job_id for application in applications})
        timeline = load_timeline(applications, grouped, titles, now=now)
        states = {state.application_id: state for state in self.states.list_for_user(user.id)}

        items: list[FollowUpItem] = []
        for entry in timeline:
            state = states.get(entry.application_id)
            if state is not None and _is_snoozed(state, now):
                continue
            days = _effective_days(entry, state, now)
            if entry.status == "Applied" and days >= settings.daily_plan_follow_up_days:
                items.append(_item(entry, days, "Follow up"))
            elif entry.status == "Interview":
                items.append(_item(entry, days, "Prepare"))
        items.sort(key=lambda item: item.days_since_update, reverse=True)

        return FollowUpList(
            items=items,
            generated_from={"applications": len(applications), "follow_ups": len(items)},
        )

    def snooze(
        self, user: User, application_id: uuid.UUID, *, days: int, now: datetime
    ) -> FollowUpStateRead:
        self._visible(user, application_id)
        until = now + timedelta(days=days)
        state = self.states.get_for_application(user.id, application_id)
        if state is None:
            state = self.states.create(
                user_id=user.id, application_id=application_id, snoozed_until=until
            )
        else:
            state.snoozed_until = until
        self.states.commit()
        return FollowUpStateRead.model_validate(state)

    def mark_done(
        self, user: User, application_id: uuid.UUID, *, now: datetime
    ) -> FollowUpStateRead:
        self._visible(user, application_id)
        state = self.states.get_for_application(user.id, application_id)
        if state is None:
            state = self.states.create(
                user_id=user.id, application_id=application_id, followed_up_at=now
            )
        else:
            state.followed_up_at = now
            state.snoozed_until = None
        self.states.commit()
        return FollowUpStateRead.model_validate(state)

    def _visible(self, user: User, application_id: uuid.UUID) -> None:
        if self.applications.get_for_user(user.id, application_id) is None:
            raise FollowUpNotFoundError


def build_follow_up_service(db: Session) -> FollowUpService:
    return FollowUpService(
        ApplicationRepository(db),
        ApplicationEventRepository(db),
        JobRepository(db),
        FollowUpStateRepository(db),
    )


def _item(entry: TimelineEntry, days: int, action: str) -> FollowUpItem:
    return FollowUpItem(
        application_id=entry.application_id,
        job_id=entry.job_id,
        title=entry.title,
        status=entry.status,
        days_since_update=days,
        action=action,
    )


def _effective_days(entry: TimelineEntry, state: FollowUpState | None, now: datetime) -> int:
    days = entry.days_since_update
    if state is not None and state.followed_up_at is not None:
        days = min(days, days_since(state.followed_up_at, now))
    return days


def _is_snoozed(state: FollowUpState, now: datetime) -> bool:
    return state.snoozed_until is not None and _aware(state.snoozed_until) > now


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
