from pydantic import BaseModel


class StageCount(BaseModel):
    stage: str
    count: int


class FunnelBucket(BaseModel):
    key: str
    total: int
    stages: list[StageCount]


class FunnelRead(BaseModel):
    stages: list[StageCount]
    total: int
    by: str | None = None
    buckets: list[FunnelBucket] = []


class RateMetric(BaseModel):
    numerator: int
    denominator: int
    value: float | None = None
    sufficient_sample: bool


class RatesBucket(BaseModel):
    key: str
    response: RateMetric
    interview: RateMetric
    offer: RateMetric
    offer_from_interview: RateMetric


class RatesRead(BaseModel):
    response: RateMetric
    interview: RateMetric
    offer: RateMetric
    offer_from_interview: RateMetric
    by: str | None = None
    buckets: list[RatesBucket] = []


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


class RejectionReasonCount(BaseModel):
    reason: str
    count: int


class RejectionReasonsRead(BaseModel):
    total_rejected: int
    catalog: list[str] = []
    reasons: list[RejectionReasonCount] = []
    uncategorized: int = 0


class AbVariant(BaseModel):
    key: str
    applied: int
    responded: int
    response_rate: float | None = None
    sufficient_sample: bool


class AbTestRead(BaseModel):
    by: str
    min_sample: int
    variants: list[AbVariant] = []
    winner: str | None = None
