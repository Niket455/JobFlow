from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.application_event_repository import ApplicationEventRepository
from app.repositories.application_repository import ApplicationRepository
from app.schemas.insights import WeeklyActivity, WeeklyReview
from app.services.daily_plan_service import DailyPlanService, build_daily_plan_service
from app.services.follow_up_service import FollowUpService, build_follow_up_service
from app.services.skill_gap_service import SkillGapService, build_skill_gap_service
from app.services.weekly_review import ActivityEvent, summarize_activity

WINDOW_DAYS = 7


class WeeklyReviewService:
    """Deterministic weekly review: recent activity, follow-ups due, top gap, priorities."""

    def __init__(
        self,
        applications: ApplicationRepository,
        events: ApplicationEventRepository,
        follow_ups: FollowUpService,
        skills: SkillGapService,
        daily_plan: DailyPlanService,
    ) -> None:
        self.applications = applications
        self.events = events
        self.follow_ups = follow_ups
        self.skills = skills
        self.daily_plan = daily_plan

    def review(self, user: User, *, now: datetime) -> WeeklyReview:
        period_end = now.date()
        period_start = (now - timedelta(days=WINDOW_DAYS - 1)).date()
        applications = self.applications.list_all_for_user(user.id)
        grouped = self.events.list_for_applications(
            [application.id for application in applications]
        )
        activity_events = [
            ActivityEvent(event_type=event.type, occurred_on=_aware(event.occurred_at).date())
            for events in grouped.values()
            for event in events
            if period_start <= _aware(event.occurred_at).date() <= period_end
        ]
        gap = self.skills.report(user)
        follow_ups = self.follow_ups.list_for_user(user, now=now)
        priorities = self.daily_plan.plan(user, now=now).items
        return WeeklyReview(
            period_start=period_start,
            period_end=period_end,
            activity=WeeklyActivity(**summarize_activity(activity_events)),
            follow_ups_due=len(follow_ups.items),
            top_gap=gap.missing[0] if gap.missing else None,
            priorities=priorities,
        )


def build_weekly_review_service(db: Session) -> WeeklyReviewService:
    return WeeklyReviewService(
        ApplicationRepository(db),
        ApplicationEventRepository(db),
        build_follow_up_service(db),
        build_skill_gap_service(db),
        build_daily_plan_service(db),
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
