from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.repositories.career_goal_repository import CareerGoalRepository
from app.schemas.career_goal import CareerGoalData, CareerGoalRead
from app.services.career_goal_service import CareerGoalService

router = APIRouter(prefix="/career-goals", tags=["career-goals"])


def _service(db: DbSession) -> CareerGoalService:
    return CareerGoalService(CareerGoalRepository(db))


@router.get("", response_model=CareerGoalRead)
def get_career_goal(current_user: CurrentUser, db: DbSession) -> CareerGoalRead:
    return _service(db).get(current_user)


@router.put("", response_model=CareerGoalRead)
def update_career_goal(
    payload: CareerGoalData, current_user: CurrentUser, db: DbSession
) -> CareerGoalRead:
    return _service(db).update(current_user, payload)
