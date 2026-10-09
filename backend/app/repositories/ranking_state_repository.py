import uuid
from typing import Any

from sqlalchemy import select

from app.models.ranking_state import RankingState
from app.repositories.base import BaseRepository


class RankingStateRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID) -> RankingState | None:
        return self.db.scalar(select(RankingState).where(RankingState.user_id == user_id))

    def create(self, **fields: Any) -> RankingState:
        state = RankingState(**fields)
        self.db.add(state)
        self.db.flush()
        return state
