import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class InterviewKit(Base):
    """A personalized set of interview questions for one job. Append-only (regenerate → new row)."""

    __tablename__ = "interview_kits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    resume_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("resume_versions.id", ondelete="SET NULL"), nullable=True
    )
    model: Mapped[str] = mapped_column(String(100))
    questions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
