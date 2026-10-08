import uuid
from typing import Any

from sqlalchemy import select

from app.models.career_goal import CareerGoal
from app.repositories.base import BaseRepository


class CareerGoalRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID) -> CareerGoal | None:
        return self.db.scalar(select(CareerGoal).where(CareerGoal.user_id == user_id))

    def upsert(self, user_id: uuid.UUID, data: dict[str, Any]) -> CareerGoal:
        goal = self.get_for_user(user_id)
        if goal is None:
            goal = CareerGoal(user_id=user_id, **data)
            self.db.add(goal)
        else:
            for key, value in data.items():
                setattr(goal, key, value)
        self.db.commit()
        self.db.refresh(goal)
        return goal
