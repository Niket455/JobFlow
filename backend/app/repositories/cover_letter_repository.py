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

    def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        job_id: uuid.UUID | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[CoverLetter]:
        query = select(CoverLetter).where(CoverLetter.user_id == user_id)
        if job_id is not None:
            query = query.where(CoverLetter.job_id == job_id)
        query = query.order_by(CoverLetter.created_at.desc()).offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return list(self.db.scalars(query))

    def create(self, **fields: Any) -> CoverLetter:
        letter = CoverLetter(**fields)
        self.db.add(letter)
        self.db.flush()
        return letter

    def delete(self, letter: CoverLetter) -> None:
        self.db.delete(letter)
        self.db.flush()
