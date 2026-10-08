import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class StarStory(Base):
    """A reusable STAR story, optionally linked to a resume item (dotted ProfileData path)."""

    __tablename__ = "star_stories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    resume_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("resume_versions.id", ondelete="SET NULL"), nullable=True
    )
    resume_item_path: Mapped[str | None] = mapped_column(String(200), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    content_enc: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
