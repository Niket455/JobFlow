from pydantic import BaseModel


class StageCount(BaseModel):
    stage: str
    count: int


class FunnelRead(BaseModel):
    stages: list[StageCount]
    total: int


class RateMetric(BaseModel):
    numerator: int
    denominator: int
    value: float | None = None
    sufficient_sample: bool


class RatesRead(BaseModel):
    response: RateMetric
    interview: RateMetric
    offer: RateMetric
    offer_from_interview: RateMetric


class RejectionBucket(BaseModel):
    key: str
    total: int
    rejected: int
    rate: float | None = None
    sufficient_sample: bool


class RejectionsRead(BaseModel):
    total_rejected: int
    by: str
    buckets: list[RejectionBucket] = []
    stages: dict[str, int] = {}
    reasons: list[str] = []
