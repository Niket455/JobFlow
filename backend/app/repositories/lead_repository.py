import uuid
from typing import Any

from sqlalchemy import select

from app.models.lead import Lead
from app.repositories.base import BaseRepository


class LeadRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID, lead_id: uuid.UUID) -> Lead | None:
        return self.db.scalar(select(Lead).where(Lead.user_id == user_id, Lead.id == lead_id))

    def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Lead]:
        query = select(Lead).where(Lead.user_id == user_id)
        if status is not None:
            query = query.where(Lead.status == status)
        return list(
            self.db.scalars(query.order_by(Lead.created_at.desc()).limit(limit).offset(offset))
        )

    def exists(self, user_id: uuid.UUID, dedupe_key: str) -> bool:
        found = self.db.scalar(
            select(Lead.id).where(Lead.user_id == user_id, Lead.dedupe_key == dedupe_key).limit(1)
        )
        return found is not None

    def create(self, **fields: Any) -> Lead:
        lead = Lead(**fields)
        self.db.add(lead)
        self.db.flush()
        return lead
