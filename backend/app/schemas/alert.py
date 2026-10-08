import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AlertData(BaseModel):
    name: str = "Job alerts"
    enabled: bool = True
    frequency: Literal["daily", "weekly"] = "daily"
    min_overall: float = 7.0
    quiet_hours_start: int | None = Field(default=None, ge=0, le=23)
    quiet_hours_end: int | None = Field(default=None, ge=0, le=23)


class AlertRead(AlertData):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    unsubscribe_token: str
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    updated_at: datetime | None = None


class AlertSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    enabled: bool
    frequency: str
    min_overall: float
    next_run_at: datetime | None = None


class AlertItem(BaseModel):
    job_id: uuid.UUID
    title: str
    company: str | None = None
    overall: float
    recommendation: str


class AlertRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: uuid.UUID
    status: str
    items_count: int
    job_ids: list[str]
    error: str | None = None
    created_at: datetime


class UnsubscribeResult(BaseModel):
    unsubscribed: bool
