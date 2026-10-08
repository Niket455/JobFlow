import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.application_event import ApplicationEvent
from app.models.job import Job
from app.models.user import User
from app.repositories.application_event_repository import ApplicationEventRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_repository import JobRepository
from app.repositories.match_repository import MatchRepository
from app.schemas.insights import DailyPlan
from app.services.application_status import StatusEvent, derive
from app.services.daily_plan import ApplicationCandidate, MatchCandidate, build_daily_plan
from app.services.skill_gap_service import SkillGapService, build_skill_gap_service


class DailyPlanService:
    """Deterministic 'today' plan derived from matches, applications, and skill gaps."""

    def __init__(
        self,
        skill_gap: SkillGapService,
        matches: MatchRepository,
        applications: ApplicationRepository,
        events: ApplicationEventRepository,
        jobs: JobRepository,
        *,
        follow_up_days: int,
        max_items: int,
    ) -> None:
        self.skill_gap = skill_gap
        self.matches = matches
        self.applications = applications
        self.events = events
        self.jobs = jobs
        self.follow_up_days = follow_up_days
        self.max_items = max_items

    def plan(self, user: User, *, now: datetime) -> DailyPlan:
        gap = self.skill_gap.report(user)
        eligible = self.matches.list_eligible(
            user.id, min_overall=settings.strong_match_threshold, since=None
        )
        applications = self.applications.list_all_for_user(user.id)
        grouped = self.events.list_for_applications(
            [application.id for application in applications]
        )
        titles = self.jobs.get_many(
            {match.job_id for match in eligible}
            | {application.job_id for application in applications}
        )
        applied_job_ids = {application.job_id for application in applications}

        matches = [
            MatchCandidate(
                job_id=match.job_id, title=_title(titles, match.job_id), overall=match.overall
            )
            for match in eligible
            if match.job_id not in applied_job_ids
        ]
        candidates = [
            ApplicationCandidate(
                application_id=application.id,
                job_id=application.job_id,
                title=_title(titles, application.job_id),
                status=_status(grouped.get(application.id, [])),
                days_since_update=_days(application.updated_at, now),
            )
            for application in applications
        ]
        skills = [item.skill for item in gap.missing[:3]]
        items = build_daily_plan(
            matches=matches,
            applications=candidates,
            skills=skills,
            follow_up_days=self.follow_up_days,
            max_items=self.max_items,
        )
        return DailyPlan(
            items=items,
            generated_from={
                "tracked_jobs": gap.total_jobs,
                "strong_matches": len(matches),
                "applications": len(applications),
                "gaps": len(gap.missing),
            },
        )


def build_daily_plan_service(db: Session) -> DailyPlanService:
    return DailyPlanService(
        build_skill_gap_service(db),
        MatchRepository(db),
        ApplicationRepository(db),
        ApplicationEventRepository(db),
        JobRepository(db),
        follow_up_days=settings.daily_plan_follow_up_days,
        max_items=settings.daily_plan_max_items,
    )


def _status(events: list[ApplicationEvent]) -> str:
    status_events = [
        StatusEvent(type=event.type, occurred_at=event.occurred_at, created_at=event.created_at)
        for event in events
    ]
    return derive(status_events)[0]


def _days(updated_at: datetime | None, now: datetime) -> int:
    if updated_at is None:
        return 0
    return max(0, (now - updated_at).days)


def _title(titles: dict[uuid.UUID, Job], job_id: uuid.UUID) -> str:
    job = titles.get(job_id)
    return job.title if job is not None else "this role"
