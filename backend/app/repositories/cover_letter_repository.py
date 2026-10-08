import uuid
from typing import Any

from sqlalchemy import select

from app.models.cover_letter import CoverLetter
from app.repositories.base import BaseRepository


class CoverLetterRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID, letter_id: uuid.UUID) -> CoverLetter | None:
        return self.db.scalar(
            select(CoverLetter).where(CoverLetter.user_id == user_id, CoverLetter.id == letter_id)
        )

    def list_for_user(self, user_id: uuid.UUID) -> list[CoverLetter]:
        return list(
            self.db.scalars(
                select(CoverLetter)
                .where(CoverLetter.user_id == user_id)
                .order_by(CoverLetter.created_at.desc())
            )
        )

    def create(self, **fields: Any) -> CoverLetter:
        letter = CoverLetter(**fields)
        self.db.add(letter)
        self.db.flush()
        return letter
