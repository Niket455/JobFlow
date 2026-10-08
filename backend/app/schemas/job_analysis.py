import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobAnalysisData(BaseModel):
    skills_required: list[str] = []
    skills_preferred: list[str] = []
    responsibilities: list[str] = []
    seniority: str | None = None
    experience_years_required: float | None = None
    education_required: str | None = None
    salary: str | None = None
    notice_expectation: str | None = None
    keywords: list[str] = []
    confidence: dict[str, float] = {}
    source_snippets: dict[str, str] = {}


class JobAnalysisRead(JobAnalysisData):
    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID
    updated_at: datetime | None = None
