import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.job_analysis import JobAnalysis
from app.models.match import Match
from app.models.user import User
from app.repositories.career_goal_repository import CareerGoalRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.deal_breakers_repository import DealBreakersRepository
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_repository import JobRepository
from app.repositories.job_source_repository import JobSourceRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.user_repository import UserRepository
from app.schemas.match import MatchRead, MatchSummary
from app.services.career_goal_service import CareerGoalService
from app.services.deal_breakers_service import DealBreakersService
from app.services.job_service import JobNotFoundError
from app.services.match_scoring import SCORING_VERSION, MatchInputs, score
from app.services.profile_service import ProfileService

RECOMPUTE_LIMIT = 1000


class MatchNotFoundError(Exception):
    pass


class MatchService:
    """Builds deterministic match inputs and records reproducible scores."""

    def __init__(
        self,
        jobs: JobRepository,
        sources: JobSourceRepository,
        analyses: JobAnalysisRepository,
        matches: MatchRepository,
        companies: CompanyRepository,
        profiles: ProfileService,
        goals: CareerGoalService,
        breakers: DealBreakersService,
    ) -> None:
        self.jobs = jobs
        self.sources = sources
        self.analyses = analyses
        self.matches = matches
        self.companies = companies
        self.profiles = profiles
        self.goals = goals
        self.breakers = breakers

    def match(self, user: User, job_id: uuid.UUID) -> MatchRead:
        job = self._visible_job(user, job_id)
        return self._record(user, job)

    def recompute(self, user: User) -> int:
        jobs = self.jobs.list_for_user(user.id, limit=RECOMPUTE_LIMIT, offset=0, status="Active")
        for job in jobs:
            self._record(user, job)
        return len(jobs)

    def list_for_user(self, user: User, *, limit: int, offset: int) -> list[MatchSummary]:
        return [
            MatchSummary.model_validate(record)
            for record in self.matches.list_for_user(user.id, limit=limit, offset=offset)
        ]

    def get(self, user: User, match_id: uuid.UUID) -> MatchRead:
        record = self.matches.get_for_user(user.id, match_id)
        if record is None:
            raise MatchNotFoundError
        return self._to_read(record)

    def _record(self, user: User, job: Job) -> MatchRead:
        analysis = self.analyses.get_for_job(job.id)
        result = score(self._inputs(user, job, analysis))
        record = self.matches.upsert(
            user.id,
            job.id,
            {
                "overall": result.overall,
                "sub_scores": result.sub_scores,
                "recommendation": result.recommendation,
                "excluded": result.excluded,
                "reasons": result.reasons,
                "evidence": result.evidence,
                "scoring_version": SCORING_VERSION,
                "resume_version_id": None,
            },
        )
        return self._to_read(record)

    def _inputs(self, user: User, job: Job, analysis: JobAnalysis | None) -> MatchInputs:
        profile = self.profiles.get(user)
        goal = self.goals.get(user)
        breakers = self.breakers.get(user)
        data: dict[str, Any] = analysis.data if analysis is not None else {}
        company = self.companies.get(job.company_id) if job.company_id is not None else None
        target_roles = ([goal.target_role] if goal.target_role else []) + profile.target_roles
        salaries = [
            value
            for value in (goal.target_salary_min, breakers.min_salary)
            if value is not None and value > 0
        ]
        return MatchInputs(
            job_title=job.title,
            job_status=job.status,
            job_location=job.location,
            job_company=company.name if company is not None else None,
            skills_required=_str_list(data.get("skills_required")),
            skills_preferred=_str_list(data.get("skills_preferred")),
            seniority=_str_or_none(data.get("seniority")),
            experience_years_required=_float_or_none(data.get("experience_years_required")),
            education_required=_str_or_none(data.get("education_required")),
            salary=_str_or_none(data.get("salary")),
            notice_expectation=_str_or_none(data.get("notice_expectation")),
            keywords=_str_list(data.get("keywords")),
            user_skills=profile.skills,
            user_experience_years=profile.experience_years,
            user_has_education=bool(profile.education),
            target_roles=target_roles,
            industries=profile.industries,
            preferred_locations=_dedupe(goal.locations + profile.preferred_locations),
            min_salary=max(salaries) if salaries else None,
            notice_period_days=profile.notice_period_days,
            excluded_companies=breakers.excluded_companies,
            excluded_locations=breakers.excluded_locations,
        )

    def _visible_job(self, user: User, job_id: uuid.UUID) -> Job:
        job = self.jobs.get(job_id)
        if job is None or not self.sources.exists(job_id, user.id):
            raise JobNotFoundError
        return job

    @staticmethod
    def _to_read(record: Match) -> MatchRead:
        return MatchRead.model_validate(
            {
                "id": record.id,
                "job_id": record.job_id,
                "overall": record.overall,
                "recommendation": record.recommendation,
                "scoring_version": record.scoring_version,
                "updated_at": record.updated_at,
                "sub_scores": record.sub_scores,
                "excluded": record.excluded,
                "reasons": record.reasons,
                "evidence": record.evidence,
                "resume_version_id": record.resume_version_id,
            }
        )


def build_match_service(db: Session) -> MatchService:
    return MatchService(
        JobRepository(db),
        JobSourceRepository(db),
        JobAnalysisRepository(db),
        MatchRepository(db),
        CompanyRepository(db),
        ProfileService(ProfileRepository(db), UserRepository(db)),
        CareerGoalService(CareerGoalRepository(db)),
        DealBreakersService(DealBreakersRepository(db)),
    )


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _str_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.lower().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result
