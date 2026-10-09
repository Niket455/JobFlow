import uuid
from typing import Any

from sqlalchemy import select

from app.models.email_message import EmailMessage
from app.repositories.base import BaseRepository


class EmailMessageRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID, message_id: uuid.UUID) -> EmailMessage | None:
        return self.db.scalar(
            select(EmailMessage).where(
                EmailMessage.user_id == user_id, EmailMessage.id == message_id
            )
        )

    def list_for_user(self, user_id: uuid.UUID, *, status: str | None = None) -> list[EmailMessage]:
        query = select(EmailMessage).where(EmailMessage.user_id == user_id)
        if status is not None:
            query = query.where(EmailMessage.status == status)
        return list(self.db.scalars(query.order_by(EmailMessage.received_at.desc())))

    def exists(self, integration_id: uuid.UUID, external_id: str) -> bool:
        found = self.db.scalar(
            select(EmailMessage.id)
            .where(
                EmailMessage.integration_id == integration_id,
                EmailMessage.external_id == external_id,
            )
            .limit(1)
        )
        return found is not None

    def create(self, **fields: Any) -> EmailMessage:
        message = EmailMessage(**fields)
        self.db.add(message)
        self.db.flush()
        return message

    def save(self, message: EmailMessage) -> None:
        self.db.commit()
        self.db.refresh(message)
