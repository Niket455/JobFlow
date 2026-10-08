import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, HttpUrl


class IngestRequest(BaseModel):
    url: HttpUrl


class JobSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    adapter: str
    url: str
    canonical_url: str
    first_seen_at: datetime
    last_seen_at: datetime


class JobSummary(BaseModel):
    id: uuid.UUID
    title: str
    company: str | None = None
    location: str | None = None
    status: str
    possible_duplicate_of_id: uuid.UUID | None = None
    first_seen_at: datetime
    last_seen_at: datetime


class JobRead(JobSummary):
    description: str | None = None
    sources: list[JobSourceRead] = []
