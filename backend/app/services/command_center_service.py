import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.job import Job
from app.models.match import Match
from app.models.user import User
from app.repositories.application_repository import ApplicationRepository
from app.repositories.career_goal_repository import CareerGoalRepository
from app.repositories.email_message_repository import EmailMessageRepository
from app.repositories.job_repository import JobRepository
from app.repositories.match_repository import MatchRepository
from app.schemas.command_center import CommandCenter, EvidenceLink, GoalSummary, Insight
from app.schemas.insights import DailyPlan, SkillGapReport
from app.services.analytics_service import AnalyticsService, build_analytics_service
from app.services.daily_plan_service import DailyPlanService, build_daily_plan_service
from app.services.skill_gap_service import SkillGapService, build_skill_gap_service


class CommandCenterService:
    """Aggregates goal, funnel, today's plan, and a top insight with evidence links."""

    def __init__(
        self,
        goals: CareerGoalRepository,
        analytics: AnalyticsService,
        daily_plan: DailyPlanService,
        matches: MatchRepository,
        applications: ApplicationRepository,
        emails: EmailMessageRepository,
        jobs: JobRepository,
        skills: SkillGapService,
    ) -> None:
        self.goals = goals
        self.analytics = analytics
        self.daily_plan = daily_plan
        self.matches = matches
        self.applications = applications
        self.emails = emails
        self.jobs = jobs
        self.skills = skills

    def build(self, user: User, *, now: datetime) -> CommandCenter:
        goal = self.goals.get_for_user(user.id)
        today = self.daily_plan.plan(user, now=now)
        gap = self.skills.report(user)
        eligible = self.matches.list_eligible(
            user.id, min_overall=settings.strong_match_threshold, since=None
        )
        applications = self.applications.list_all_for_user(user.id)
        pending = self.emails.list_for_user(user.id, status="pending")
        titles = self.jobs.get_many({match.job_id for match in eligible})

        return CommandCenter(
            goal=(
                GoalSummary(
                    target_role=goal.target_role,
                    target_date=goal.target_date,
                    locations=goal.locations,
                )
                if goal is not None
                else None
            ),
            funnel=self.analytics.funnel(user),
            today=today,
            insight=_insight(today, gap, eligible, titles),
            counts={
                "tracked_jobs": gap.total_jobs,
                "applications": len(applications),
                "strong_matches": len(eligible),
                "pending_emails": len(pending),
                "skill_gaps": len(gap.missing),
            },
        )


def build_command_center_service(db: Session) -> CommandCenterService:
    return CommandCenterService(
        CareerGoalRepository(db),
        build_analytics_service(db),
        build_daily_plan_service(db),
        MatchRepository(db),
        ApplicationRepository(db),
        EmailMessageRepository(db),
        JobRepository(db),
        build_skill_gap_service(db),
    )


def _insight(
    today: DailyPlan,
    gap: SkillGapReport,
    eligible: list[Match],
    titles: dict[uuid.UUID, Job],
) -> Insight:
    interviews = [item for item in today.items if item.kind == "interview_prep"]
    if interviews:
        first = interviews[0]
        return Insight(
            headline=f"{len(interviews)} interview(s) in progress",
            detail="Practice your answers before the call.",
            evidence=[
                EvidenceLink(kind="application", label=first.title, ref_id=first.application_id)
            ],
        )
    if gap.missing:
        top = gap.missing[0]
        return Insight(
            headline=f"Close the {top.skill} gap",
            detail=f"{top.demand_pct}% of your tracked jobs ask for {top.skill}.",
            evidence=[EvidenceLink(kind="skill", label=top.skill)],
        )
    if eligible:
        return Insight(
            headline=f"{len(eligible)} strong match(es) to review",
            detail="These jobs score above your strong-match threshold.",
            evidence=[
                EvidenceLink(kind="job", label=_title(titles, match.job_id), ref_id=match.job_id)
                for match in eligible[:3]
            ],
        )
    return Insight(headline="Get started", detail="Ingest a job and run a match to see insights.")


def _title(titles: dict[uuid.UUID, Job], job_id: uuid.UUID) -> str:
    job = titles.get(job_id)
    return job.title if job is not None else "Strong match"
