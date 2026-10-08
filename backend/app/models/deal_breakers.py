import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DealBreakers(Base):
    __tablename__ = "deal_breakers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    min_salary: Mapped[int | None] = mapped_column(Integer, nullable=True)
    excluded_companies: Mapped[list[str]] = mapped_column(JSON, default=list)
    excluded_locations: Mapped[list[str]] = mapped_column(JSON, default=list)
    no_night_shifts: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
