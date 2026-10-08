import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MatchEvidence(BaseModel):
    matched: list[str] = []
    partial: list[str] = []
    missing: list[str] = []


class MatchSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    overall: float
    recommendation: str
    scoring_version: str
    updated_at: datetime | None = None


class MatchRead(MatchSummary):
    sub_scores: dict[str, float] = {}
    excluded: bool = False
    reasons: list[str] = []
    evidence: MatchEvidence = Field(default_factory=MatchEvidence)
    resume_version_id: uuid.UUID | None = None
