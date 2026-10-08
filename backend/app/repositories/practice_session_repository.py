import uuid
from typing import Any

from sqlalchemy import select

from app.models.practice_session import PracticeSession
from app.repositories.base import BaseRepository


class PracticeSessionRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID, session_id: uuid.UUID) -> PracticeSession | None:
        return self.db.scalar(
            select(PracticeSession).where(
                PracticeSession.user_id == user_id, PracticeSession.id == session_id
            )
        )

    def list_for_user(self, user_id: uuid.UUID) -> list[PracticeSession]:
        return list(
            self.db.scalars(
                select(PracticeSession)
                .where(PracticeSession.user_id == user_id)
                .order_by(PracticeSession.created_at.desc())
            )
        )

    def create(self, **fields: Any) -> PracticeSession:
        session = PracticeSession(**fields)
        self.db.add(session)
        self.db.flush()
        return session
