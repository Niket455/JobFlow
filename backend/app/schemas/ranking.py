import uuid
from datetime import datetime

from pydantic import BaseModel


class RankingAdjustment(BaseModel):
    company: str
    sample: int
    response_rate: float
    boost: float


class RankingItem(BaseModel):
    job_id: uuid.UUID
    title: str
    company: str | None = None
    base: float
    boost: float
    score: float
    reasons: list[str] = []


class RankingRead(BaseModel):
    reset_at: datetime | None = None
    min_sample: int
    adjustments: list[RankingAdjustment] = []
    items: list[RankingItem] = []


class RankingStateRead(BaseModel):
    reset_at: datetime | None = None
