from app.models.user import User
from app.repositories.career_goal_repository import CareerGoalRepository
from app.schemas.career_goal import CareerGoalData, CareerGoalRead


class CareerGoalService:
    def __init__(self, goals: CareerGoalRepository) -> None:
        self.goals = goals

    def get(self, user: User) -> CareerGoalRead:
        record = self.goals.get_for_user(user.id)
        if record is None:
            return CareerGoalRead()
        return CareerGoalRead.model_validate(record)

    def update(self, user: User, payload: CareerGoalData) -> CareerGoalRead:
        record = self.goals.upsert(user.id, payload.model_dump())
        return CareerGoalRead.model_validate(record)
