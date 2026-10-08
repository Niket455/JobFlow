import uuid
from typing import Any

from sqlalchemy import select

from app.models.deal_breakers import DealBreakers
from app.repositories.base import BaseRepository


class DealBreakersRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID) -> DealBreakers | None:
        return self.db.scalar(select(DealBreakers).where(DealBreakers.user_id == user_id))

    def upsert(self, user_id: uuid.UUID, data: dict[str, Any]) -> DealBreakers:
        record = self.get_for_user(user_id)
        if record is None:
            record = DealBreakers(user_id=user_id, **data)
            self.db.add(record)
        else:
            for key, value in data.items():
                setattr(record, key, value)
        self.db.commit()
        self.db.refresh(record)
        return record
