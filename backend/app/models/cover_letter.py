import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CoverLetter(Base):
    """An append-only cover-letter version, grounded claim-by-claim in the resume/JD."""

    __tablename__ = "cover_letters"

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
    parent_letter_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("cover_letters.id", ondelete="SET NULL"), nullable=True
    )
    label: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100))
    subject: Mapped[str] = mapped_column(String(255))
    body_enc: Mapped[str] = mapped_column(Text)
    grounding: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
