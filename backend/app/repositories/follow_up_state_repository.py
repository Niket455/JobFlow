import uuid
from typing import Any

from sqlalchemy import select

from app.models.follow_up_state import FollowUpState
from app.repositories.base import BaseRepository


class FollowUpStateRepository(BaseRepository):
    def get_for_application(
        self, user_id: uuid.UUID, application_id: uuid.UUID
    ) -> FollowUpState | None:
        return self.db.scalar(
            select(FollowUpState).where(
                FollowUpState.user_id == user_id,
                FollowUpState.application_id == application_id,
            )
        )

    def list_for_user(self, user_id: uuid.UUID) -> list[FollowUpState]:
        return list(self.db.scalars(select(FollowUpState).where(FollowUpState.user_id == user_id)))

    def create(self, **fields: Any) -> FollowUpState:
        state = FollowUpState(**fields)
        self.db.add(state)
        self.db.flush()
        return state
