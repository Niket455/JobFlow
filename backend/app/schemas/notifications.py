import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    title: str
    body: str | None = None
    job_id: uuid.UUID | None = None
    application_id: uuid.UUID | None = None
    read_at: datetime | None = None
    created_at: datetime


class UnreadCount(BaseModel):
    unread: int


class RefreshResult(BaseModel):
    created: int
    existing: int


class DeliverResult(BaseModel):
    delivered: int
