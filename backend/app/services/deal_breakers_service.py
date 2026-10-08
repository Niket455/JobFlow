from app.models.user import User
from app.repositories.deal_breakers_repository import DealBreakersRepository
from app.schemas.deal_breakers import DealBreakersData, DealBreakersRead


class DealBreakersService:
    def __init__(self, deal_breakers: DealBreakersRepository) -> None:
        self.deal_breakers = deal_breakers

    def get(self, user: User) -> DealBreakersRead:
        record = self.deal_breakers.get_for_user(user.id)
        if record is None:
            return DealBreakersRead()
        return DealBreakersRead.model_validate(record)

    def update(self, user: User, payload: DealBreakersData) -> DealBreakersRead:
        record = self.deal_breakers.upsert(user.id, payload.model_dump())
        return DealBreakersRead.model_validate(record)
