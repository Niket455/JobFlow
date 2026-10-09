import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LeadSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    url: str
    domain: str | None = None
    status: str
    rough_score: float | None = None
    discovery_source_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    created_at: datetime


class LeadRead(LeadSummary):
    canonical_url: str


class DiscoverySourceCreate(BaseModel):
    kind: str
    label: str
    target: str


class DiscoverySourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    label: str
    target: str
    enabled: bool
    last_run_at: datetime | None = None
    last_status: str | None = None
    created_at: datetime


class DiscoverRunResult(BaseModel):
    created: int
    existing: int
