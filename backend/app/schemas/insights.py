import uuid

from pydantic import BaseModel


class SkillDemand(BaseModel):
    skill: str
    jobs: int
    demand_pct: float


class SkillGapReport(BaseModel):
    total_jobs: int
    have: list[SkillDemand] = []
    missing: list[SkillDemand] = []


class PlanItem(BaseModel):
    kind: str
    title: str
    detail: str
    priority: int
    job_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None


class DailyPlan(BaseModel):
    items: list[PlanItem] = []
    generated_from: dict[str, int] = {}


class LearningItem(BaseModel):
    skill: str
    priority: int
    demand_pct: float
    jobs: int
    rationale: str


class LearningRoadmap(BaseModel):
    items: list[LearningItem] = []
    total_jobs: int
