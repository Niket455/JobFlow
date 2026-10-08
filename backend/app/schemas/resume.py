import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.profile import ProfileData


class ResumeExtraction(ProfileData):
    """LLM extraction result: profile fields plus per-section confidence."""

    confidence: dict[str, float] = {}


class ResumeVersionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    is_master: bool
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


class ResumeVersionRead(ResumeVersionSummary):
    confidence: dict[str, float] | None = None
    parsed: ProfileData | None = None
