from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.repositories.deal_breakers_repository import DealBreakersRepository
from app.schemas.deal_breakers import DealBreakersData, DealBreakersRead
from app.services.deal_breakers_service import DealBreakersService

router = APIRouter(prefix="/deal-breakers", tags=["deal-breakers"])


def _service(db: DbSession) -> DealBreakersService:
    return DealBreakersService(DealBreakersRepository(db))


@router.get("", response_model=DealBreakersRead)
def get_deal_breakers(current_user: CurrentUser, db: DbSession) -> DealBreakersRead:
    return _service(db).get(current_user)


@router.put("", response_model=DealBreakersRead)
def update_deal_breakers(
    payload: DealBreakersData, current_user: CurrentUser, db: DbSession
) -> DealBreakersRead:
    return _service(db).update(current_user, payload)
