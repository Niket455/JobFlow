import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InterviewQuestionDraft(BaseModel):
    category: str
    question: str
    intent: str = ""
    hint: str = ""
    answer_outline: list[str] = []


class InterviewKitDraft(BaseModel):
    questions: list[InterviewQuestionDraft] = []


class RubricCriterion(BaseModel):
    name: str
    score: int
    max_score: int = 5
    comment: str = ""


class AnswerFeedback(BaseModel):
    overall: int = 0
    criteria: list[RubricCriterion] = []
    strengths: list[str] = []
    improvements: list[str] = []


class StarStoryDraft(BaseModel):
    title: str = ""
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""
    skills: list[str] = []


class InterviewKitRequest(BaseModel):
    job_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None


class InterviewKitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    resume_version_id: uuid.UUID | None = None
    model: str
    questions: list[InterviewQuestionDraft] = []
    created_at: datetime


class InterviewKitSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    question_count: int
    created_at: datetime


class PracticeRequest(BaseModel):
    question: str
    answer: str
    job_id: uuid.UUID | None = None
    category: str | None = None
    duration_seconds: int | None = Field(default=None, ge=0)


class AnswerSignalsRead(BaseModel):
    word_count: int
    has_metric: bool
    star_coverage: dict[str, bool]


class PracticeSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID | None = None
    question: str
    category: str
    duration_seconds: int | None = None
    answer: str
    rubric: AnswerFeedback
    score: int
    signals: AnswerSignalsRead
    created_at: datetime


class PracticeSessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    question: str
    category: str
    score: int
    duration_seconds: int | None = None
    created_at: datetime


class StarStoryCreate(BaseModel):
    title: str
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""
    skills: list[str] = []
    resume_version_id: uuid.UUID | None = None
    resume_item_path: str | None = None


class StarStoryUpdate(BaseModel):
    title: str | None = None
    situation: str | None = None
    task: str | None = None
    action: str | None = None
    result: str | None = None
    skills: list[str] | None = None
    resume_version_id: uuid.UUID | None = None
    resume_item_path: str | None = None


class StarStoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    situation: str
    task: str
    action: str
    result: str
    skills: list[str] = []
    resume_version_id: uuid.UUID | None = None
    resume_item_path: str | None = None
    created_at: datetime
    updated_at: datetime


class StarStorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    skills: list[str] = []
    resume_version_id: uuid.UUID | None = None
    created_at: datetime


class StarStoryDraftRequest(BaseModel):
    resume_version_id: uuid.UUID
    path: str
