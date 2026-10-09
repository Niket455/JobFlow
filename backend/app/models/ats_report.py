import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AtsReportRecord(Base):
    """A persisted ATS report snapshot for a resume version, optionally scored against a job."""

    __tablename__ = "ats_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    resume_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("resume_versions.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    score: Mapped[int] = mapped_column(Integer)
    grade: Mapped[str] = mapped_column(String(2))
    report: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
