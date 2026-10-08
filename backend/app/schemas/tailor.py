import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProposedChange(BaseModel):
    path: str
    new_text: str
    source_span: str | None = None


class TailorProposal(BaseModel):
    changes: list[ProposedChange] = []


class TailorRequest(BaseModel):
    job_id: uuid.UUID
    instructions: str | None = None


class TailorChange(BaseModel):
    path: str
    old_text: str | None = None
    new_text: str
    source_span: str | None = None
    grounded: bool
    decision: Literal["approved", "rejected", "pending"]


class TailorRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    base_resume_version_id: uuid.UUID
    job_id: uuid.UUID
    status: str
    model: str
    changes: list[TailorChange] = []
    applied_resume_version_id: uuid.UUID | None = None
    created_at: datetime


class DecisionUpdate(BaseModel):
    index: int = Field(ge=0)
    decision: Literal["approved", "rejected", "pending"]


class TailorDecisions(BaseModel):
    decisions: list[DecisionUpdate] = []
