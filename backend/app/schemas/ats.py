import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AtsCheck(BaseModel):
    id: str
    label: str
    score: int
    max_score: int
    passed: bool
    detail: str


class AtsParseTest(BaseModel):
    passed: bool
    extracted: dict[str, bool]
    missing: list[str]


class AtsKeyword(BaseModel):
    matched: list[str]
    missing: list[str]
    coverage: float


class AtsReport(BaseModel):
    score: int
    grade: str
    parse_test: AtsParseTest
    checks: list[AtsCheck]
    keywords: AtsKeyword | None = None
    recommendations: list[str] = []


class AtsReportRequest(BaseModel):
    job_id: uuid.UUID | None = None


class AtsReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resume_version_id: uuid.UUID
    job_id: uuid.UUID | None = None
    score: int
    grade: str
    created_at: datetime


class AtsReportRead(AtsReportSummary):
    report: AtsReport
