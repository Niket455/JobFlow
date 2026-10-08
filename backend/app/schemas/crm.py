import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

Relationship = Literal["recruiter", "referral", "hiring_manager", "other"]
OutreachKind = Literal["referral", "recruiter", "followup"]


class ContactCreate(BaseModel):
    name: str
    title: str | None = None
    company_id: uuid.UUID | None = None
    company_name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    relationship: Relationship = "other"
    notes: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    title: str | None = None
    company_id: uuid.UUID | None = None
    company_name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    relationship: Relationship | None = None
    notes: str | None = None


class ContactSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    company_name: str | None = None
    relationship: str
    last_contacted_at: datetime | None = None


class ContactRead(BaseModel):
    id: uuid.UUID
    name: str
    title: str | None = None
    company_id: uuid.UUID | None = None
    company_name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    relationship: str
    notes: str | None = None
    last_contacted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class OutreachClaim(BaseModel):
    text: str
    source_span: str | None = None


class OutreachDraftProposal(BaseModel):
    subject: str = ""
    body: str = ""
    claims: list[OutreachClaim] = []


class OutreachRequest(BaseModel):
    contact_id: uuid.UUID
    kind: OutreachKind = "referral"
    job_id: uuid.UUID | None = None
    resume_version_id: uuid.UUID | None = None
    instructions: str | None = None


class OutreachClaimRead(BaseModel):
    text: str
    source_span: str | None = None
    grounded: bool


class OutreachDraftRead(BaseModel):
    id: uuid.UUID
    contact_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    kind: str
    subject: str
    body: str
    model: str
    claims: list[OutreachClaimRead] = []
    blocked_count: int = 0
    status: str
    created_at: datetime


class OutreachDraftSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contact_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    kind: str
    subject: str
    status: str
    created_at: datetime
