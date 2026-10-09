from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.repositories.application_event_repository import ApplicationEventRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.ranking_state_repository import RankingStateRepository
from app.schemas.ranking import RankingAdjustment, RankingItem, RankingRead, RankingStateRead

_RESPONSE_EVENTS = {"screening", "interview", "assessment", "offer"}
_MAX_BOOST = 1.0


class RankingService:
    """A transparent, resettable personalization layer on top of the reproducible base score."""

    def __init__(
        self,
        matches: MatchRepository,
        jobs: JobRepository,
        companies: CompanyRepository,
        applications: ApplicationRepository,
        events: ApplicationEventRepository,
        states: RankingStateRepository,
    ) -> None:
        self.matches = matches
        self.jobs = jobs
        self.companies = companies
        self.applications = applications
        self.events = events
        self.states = states

    def reset(self, user: User, *, now: datetime) -> RankingStateRead:
        state = self.states.get_for_user(user.id)
        if state is None:
            state = self.states.create(user_id=user.id, reset_at=now)
        else:
            state.reset_at = now
        self.states.commit()
        return RankingStateRead(reset_at=state.reset_at)

    def ranking(self, user: User, *, limit: int) -> RankingRead:
        state = self.states.get_for_user(user.id)
        reset_at = state.reset_at if state is not None else None
        adjustments = self._adjustments(user, reset_at)
        eligible = self.matches.list_eligible(
            user.id, min_overall=settings.strong_match_threshold, since=None
        )
        jobs = self.jobs.get_many({match.job_id for match in eligible})
        companies = self.companies.get_many(
            {job.company_id for job in jobs.values() if job.company_id is not None}
        )
        items: list[RankingItem] = []
        for match in eligible:
            job = jobs.get(match.job_id)
            company = (
                companies.get(job.company_id)
                if job is not None and job.company_id is not None
                else None
            )
            name = company.name if company is not None else None
            adjustment = adjustments.get(name) if name is not None else None
            boost = adjustment.boost if adjustment is not None else 0.0
            score = round(min(10.0, max(0.0, match.overall + boost)), 2)
            reasons = [f"base {match.overall:.1f}/10"]
            if adjustment is not None and boost:
                sign = "+" if boost > 0 else ""
                reasons.append(
                    f"{sign}{boost:.2f} from {name} response rate "
                    f"({adjustment.response_rate:.0%}, n={adjustment.sample})"
                )
            items.append(
                RankingItem(
                    job_id=match.job_id,
                    title=job.title if job is not None else "this role",
                    company=name,
                    base=match.overall,
                    boost=boost,
                    score=score,
                    reasons=reasons,
                )
            )
        items.sort(key=lambda item: item.score, reverse=True)
        return RankingRead(
            reset_at=reset_at,
            min_sample=settings.analytics_min_sample,
            adjustments=[adjustments[key] for key in sorted(adjustments)],
            items=items[:limit],
        )

    def _adjustments(self, user: User, reset_at: datetime | None) -> dict[str, RankingAdjustment]:
        if reset_at is not None:
            reset_at = _aware(reset_at)
        applications = self.applications.list_all_for_user(user.id)
        grouped = self.events.list_for_applications(
            [application.id for application in applications]
        )
        jobs = self.jobs.get_many({application.job_id for application in applications})
        companies = self.companies.get_many(
            {job.company_id for job in jobs.values() if job.company_id is not None}
        )
        outcomes: dict[str, list[bool]] = {}
        for application in applications:
            if reset_at is not None and (
                application.updated_at is None or _aware(application.updated_at) <= reset_at
            ):
                continue
            job = jobs.get(application.job_id)
            company = (
                companies.get(job.company_id)
                if job is not None and job.company_id is not None
                else None
            )
            if company is None:
                continue
            responded = any(
                event.type.strip().lower() in _RESPONSE_EVENTS
                for event in grouped.get(application.id, [])
            )
            outcomes.setdefault(company.name, []).append(responded)

        adjustments: dict[str, RankingAdjustment] = {}
        for name, results in outcomes.items():
            sample = len(results)
            if sample < settings.analytics_min_sample:
                continue
            rate = sum(1 for result in results if result) / sample
            adjustments[name] = RankingAdjustment(
                company=name,
                sample=sample,
                response_rate=round(rate, 4),
                boost=round(max(-_MAX_BOOST, min(_MAX_BOOST, (rate - 0.5) * 2)), 2),
            )
        return adjustments


def build_ranking_service(db: Session) -> RankingService:
    return RankingService(
        MatchRepository(db),
        JobRepository(db),
        CompanyRepository(db),
        ApplicationRepository(db),
        ApplicationEventRepository(db),
        RankingStateRepository(db),
    )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
