from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.insights import LearningItem, LearningRoadmap
from app.services.learning_roadmap import build_roadmap
from app.services.skill_gap_service import SkillGapService, build_skill_gap_service


class LearningRoadmapService:
    """Deterministic learning roadmap projected from the skill gap."""

    def __init__(self, skill_gap: SkillGapService) -> None:
        self.skill_gap = skill_gap

    def roadmap(self, user: User) -> LearningRoadmap:
        report = self.skill_gap.report(user)
        items = build_roadmap(
            [(demand.skill, demand.jobs, demand.demand_pct) for demand in report.missing]
        )
        return LearningRoadmap(
            items=[
                LearningItem(
                    skill=item.skill,
                    priority=item.priority,
                    demand_pct=item.demand_pct,
                    jobs=item.jobs,
                    rationale=item.rationale,
                )
                for item in items
            ],
            total_jobs=report.total_jobs,
        )


def build_learning_roadmap_service(db: Session) -> LearningRoadmapService:
    return LearningRoadmapService(build_skill_gap_service(db))
