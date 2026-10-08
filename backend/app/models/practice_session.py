import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class PracticeSession(Base):
    """One timed practice answer with its LLM rubric. Append-only history."""

    __tablename__ = "practice_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=True
    )
    question: Mapped[str] = mapped_column(String(1000))
    category: Mapped[str] = mapped_column(String(30), default="general")
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    answer_enc: Mapped[str] = mapped_column(Text)
    rubric: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    score: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
