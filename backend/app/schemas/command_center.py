import uuid
from datetime import date

from pydantic import BaseModel

from app.schemas.analytics import FunnelRead
from app.schemas.insights import DailyPlan


class GoalSummary(BaseModel):
    target_role: str | None = None
    target_date: date | None = None
    locations: list[str] = []


class EvidenceLink(BaseModel):
    kind: str
    label: str
    ref_id: uuid.UUID | None = None


class Insight(BaseModel):
    headline: str
    detail: str
    evidence: list[EvidenceLink] = []


class CommandCenter(BaseModel):
    goal: GoalSummary | None = None
    funnel: FunnelRead
    today: DailyPlan
    insight: Insight
    counts: dict[str, int] = {}
