import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CoverLetterClaim(BaseModel):
    text: str
    source_span: str | None = None


class CoverLetterDraft(BaseModel):
    subject: str = ""
    body: str = ""
    claims: list[CoverLetterClaim] = []


class CoverLetterRequest(BaseModel):
    job_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    instructions: str | None = None


class CoverLetterReviseRequest(BaseModel):
    instructions: str | None = None


class CoverLetterClaimRead(BaseModel):
    text: str
    source_span: str | None = None
    grounded: bool


class CoverLetterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    parent_letter_id: uuid.UUID | None = None
    label: str
    model: str
    subject: str
    body: str
    claims: list[CoverLetterClaimRead] = []
    blocked_count: int = 0
    created_at: datetime


class CoverLetterSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    label: str
    subject: str
    created_at: datetime
