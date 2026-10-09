import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    source: str | None = None
    applied_at: datetime | None = None


class CaptureRequest(BaseModel):
    url: HttpUrl
    applied_at: datetime | None = None
    source: str | None = None


class ApplicationEventCreate(BaseModel):
    type: str
    payload: dict[str, object] = Field(default_factory=dict)
    occurred_at: datetime | None = None


class ApplicationEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    payload: dict[str, object]
    occurred_at: datetime
    created_at: datetime


class ApplicationSummary(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    status: str
    kanban: str
    applied_at: datetime | None = None
    resume_version_id: uuid.UUID | None = None
    source: str | None = None
    updated_at: datetime | None = None


class ApplicationRead(ApplicationSummary):
    events: list[ApplicationEventRead] = []
