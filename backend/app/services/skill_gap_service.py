from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text
from app.models.user import User
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_repository import JobRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.user_repository import UserRepository
from app.schemas.insights import SkillDemand as SkillDemandRead
from app.schemas.insights import SkillGapReport
from app.schemas.profile import ProfileData
from app.services.encryption import ensure_data_key
from app.services.skill_gap import SkillDemand, analyze_skill_gap, job_terms

_TRACKED_JOBS_LIMIT = 500


class SkillGapService:
    """Deterministic demand analysis over the user's tracked jobs vs their profile skills."""

    def __init__(
        self,
        profiles: ProfileRepository,
        users: UserRepository,
        jobs: JobRepository,
        analyses: JobAnalysisRepository,
    ) -> None:
        self.profiles = profiles
        self.users = users
        self.jobs = jobs
        self.analyses = analyses

    def report(self, user: User) -> SkillGapReport:
        tracked = self.jobs.list_for_user(user.id, limit=_TRACKED_JOBS_LIMIT, offset=0)
        analyses = self.analyses.get_for_jobs({job.id for job in tracked})
        job_term_lists = [job_terms(record.data) for record in analyses.values()]
        gap = analyze_skill_gap(self._profile_skills(user), job_term_lists)
        return SkillGapReport(
            total_jobs=gap.total_jobs,
            have=[_demand(item) for item in gap.have],
            missing=[_demand(item) for item in gap.missing],
        )

    def _profile_skills(self, user: User) -> list[str]:
        record = self.profiles.get_for_user(user.id)
        if record is None:
            return []
        data_key = ensure_data_key(user, self.users)
        profile = ProfileData.model_validate_json(decrypt_text(data_key, record.data_enc))
        return profile.skills


def build_skill_gap_service(db: Session) -> SkillGapService:
    return SkillGapService(
        ProfileRepository(db),
        UserRepository(db),
        JobRepository(db),
        JobAnalysisRepository(db),
    )


def _demand(item: SkillDemand) -> SkillDemandRead:
    return SkillDemandRead(skill=item.skill, jobs=item.jobs, demand_pct=item.demand_pct)
