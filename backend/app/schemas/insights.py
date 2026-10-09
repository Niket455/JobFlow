import uuid
from datetime import date

from pydantic import BaseModel


class SkillDemand(BaseModel):
    skill: str
    jobs: int
    demand_pct: float
    coverage_gain: int = 0


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


class WeeklyActivity(BaseModel):
    applied: int = 0
    interview: int = 0
    offer: int = 0
    rejected: int = 0
    withdrawn: int = 0


class WeeklyReview(BaseModel):
    period_start: date
    period_end: date
    activity: WeeklyActivity
    follow_ups_due: int = 0
    top_gap: SkillDemand | None = None
    priorities: list[PlanItem] = []
