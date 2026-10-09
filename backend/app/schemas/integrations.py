import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

EmailType = Literal[
    "rejection",
    "interview",
    "offer",
    "acknowledgement",
    "recruiter_outreach",
    "other",
]


class IntegrationCreate(BaseModel):
    provider: str
    email_address: str | None = None


class IntegrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    email_address: str | None = None
    status: str
    created_at: datetime


class SyncResult(BaseModel):
    created: int
    skipped: int


class EmailClassification(BaseModel):
    classification: EmailType = "other"
    confidence: float = 0.0
    suggested_event: str | None = None
    rationale: str = ""


class EmailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    integration_id: uuid.UUID | None = None
    sender: str
    subject: str
    snippet: str
    received_at: datetime
    classification: str
    confidence: float
    application_id: uuid.UUID | None = None
    suggested_event: str | None = None
    status: str
    created_at: datetime


class EmailSuggestion(BaseModel):
    application_id: uuid.UUID | None = None
    event_type: str | None = None
    rationale: str | None = None
    confidence: float


class CalendarCreate(BaseModel):
    application_id: uuid.UUID | None = None
    kind: str = "other"
    title: str
    proposed_at: datetime | None = None
    notes: str | None = None


class CalendarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID | None = None
    kind: str
    title: str
    proposed_at: datetime | None = None
    notes: str | None = None
    status: str
    created_at: datetime
