import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification
from app.models.user import User
from app.repositories.application_event_repository import ApplicationEventRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.email_message_repository import EmailMessageRepository
from app.repositories.job_repository import JobRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.notifications import NotificationRead, RefreshResult
from app.services.application_timeline import job_title, load_timeline
from app.services.notification_center import derive_notifications
from app.services.skill_gap_service import SkillGapService, build_skill_gap_service


class NotificationNotFoundError(Exception):
    pass


class NotificationCenterService:
    """A persisted in-app feed, refreshed idempotently from current state."""

    def __init__(
        self,
        notifications: NotificationRepository,
        applications: ApplicationRepository,
        events: ApplicationEventRepository,
        jobs: JobRepository,
        matches: MatchRepository,
        emails: EmailMessageRepository,
        users: UserRepository,
        skills: SkillGapService,
    ) -> None:
        self.notifications = notifications
        self.applications = applications
        self.events = events
        self.jobs = jobs
        self.matches = matches
        self.emails = emails
        self.users = users
        self.skills = skills

    def refresh(self, user: User, *, now: datetime) -> RefreshResult:
        applications = self.applications.list_all_for_user(user.id)
        grouped = self.events.list_for_applications(
            [application.id for application in applications]
        )
        titles = self.jobs.get_many({application.job_id for application in applications})
        timeline = load_timeline(applications, grouped, titles, now=now)

        stale = [
            (entry.application_id, entry.job_id, entry.title, entry.days_since_update)
            for entry in timeline
            if entry.status == "Applied"
            and entry.days_since_update >= settings.daily_plan_follow_up_days
        ]
        interviews = [
            (entry.application_id, entry.job_id, entry.title)
            for entry in timeline
            if entry.status == "Interview"
        ]

        eligible = self.matches.list_eligible(
            user.id, min_overall=settings.strong_match_threshold, since=None
        )
        applied_job_ids = {application.job_id for application in applications}
        match_titles = self.jobs.get_many({match.job_id for match in eligible})
        strong = [
            (match.job_id, job_title(match_titles, match.job_id), match.overall)
            for match in eligible
            if match.job_id not in applied_job_ids
        ]

        pending_emails = [
            (message.id, message.subject)
            for message in self.emails.list_for_user(user.id, status="pending")
        ]

        gap = self.skills.report(user)
        top_gap = (gap.missing[0].skill, gap.missing[0].demand_pct) if gap.missing else None

        drafts = derive_notifications(
            stale_applications=stale,
            interviews=interviews,
            strong_matches=strong,
            pending_emails=pending_emails,
            top_gap=top_gap,
        )
        created = 0
        existing = 0
        for draft in drafts:
            if self.notifications.exists(user.id, draft.dedupe_key):
                existing += 1
                continue
            self.notifications.create(
                user_id=user.id,
                kind=draft.kind,
                title=draft.title,
                body=draft.body,
                job_id=draft.job_id,
                application_id=draft.application_id,
                dedupe_key=draft.dedupe_key,
            )
            created += 1
        self.notifications.commit()
        return RefreshResult(created=created, existing=existing)

    def refresh_all(self, *, now: datetime, limit: int) -> int:
        created = 0
        for user in self.users.list_active(limit=limit):
            created += self.refresh(user, now=now).created
        return created

    def list_for_user(self, user: User, *, unread_only: bool, limit: int) -> list[NotificationRead]:
        return [
            NotificationRead.model_validate(notification)
            for notification in self.notifications.list_for_user(
                user.id, unread_only=unread_only, limit=limit
            )
        ]

    def unread_count(self, user: User) -> int:
        return self.notifications.unread_count(user.id)

    def mark_read(
        self, user: User, notification_id: uuid.UUID, *, now: datetime
    ) -> NotificationRead:
        notification = self._get(user, notification_id)
        if notification.read_at is None:
            notification.read_at = now
            self.notifications.save(notification)
        return NotificationRead.model_validate(notification)

    def mark_all_read(self, user: User, *, now: datetime) -> int:
        return self.notifications.mark_all_read(user.id, now=now)

    def delete(self, user: User, notification_id: uuid.UUID) -> None:
        self.notifications.delete(self._get(user, notification_id))

    def _get(self, user: User, notification_id: uuid.UUID) -> Notification:
        notification = self.notifications.get_for_user(user.id, notification_id)
        if notification is None:
            raise NotificationNotFoundError
        return notification


def build_notification_center_service(db: Session) -> NotificationCenterService:
    return NotificationCenterService(
        NotificationRepository(db),
        ApplicationRepository(db),
        ApplicationEventRepository(db),
        JobRepository(db),
        MatchRepository(db),
        EmailMessageRepository(db),
        UserRepository(db),
        build_skill_gap_service(db),
    )
