import uuid
from typing import Any

from sqlalchemy import select

from app.models.interview_kit import InterviewKit
from app.repositories.base import BaseRepository


class InterviewKitRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID, kit_id: uuid.UUID) -> InterviewKit | None:
        return self.db.scalar(
            select(InterviewKit).where(InterviewKit.user_id == user_id, InterviewKit.id == kit_id)
        )

    def list_for_user(
        self, user_id: uuid.UUID, *, job_id: uuid.UUID | None = None
    ) -> list[InterviewKit]:
        query = select(InterviewKit).where(InterviewKit.user_id == user_id)
        if job_id is not None:
            query = query.where(InterviewKit.job_id == job_id)
        return list(self.db.scalars(query.order_by(InterviewKit.created_at.desc())))

    def create(self, **fields: Any) -> InterviewKit:
        kit = InterviewKit(**fields)
        self.db.add(kit)
        self.db.flush()
        return kit
