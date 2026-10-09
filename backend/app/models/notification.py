import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Notification(Base):
    """A persisted in-app notification. `dedupe_key` makes refresh idempotent per user."""

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "dedupe_key", name="uq_notification_user_dedupe"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    dedupe_key: Mapped[str] = mapped_column(String(120))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
