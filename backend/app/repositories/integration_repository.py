import uuid
from typing import Any

from sqlalchemy import select

from app.models.integration import Integration
from app.repositories.base import BaseRepository


class IntegrationRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID, integration_id: uuid.UUID) -> Integration | None:
        return self.db.scalar(
            select(Integration).where(
                Integration.user_id == user_id, Integration.id == integration_id
            )
        )

    def list_for_user(self, user_id: uuid.UUID) -> list[Integration]:
        return list(
            self.db.scalars(
                select(Integration)
                .where(Integration.user_id == user_id)
                .order_by(Integration.created_at.desc())
            )
        )

    def create(self, **fields: Any) -> Integration:
        integration = Integration(**fields)
        self.db.add(integration)
        self.db.commit()
        self.db.refresh(integration)
        return integration

    def delete(self, integration: Integration) -> None:
        self.db.delete(integration)
        self.db.commit()
