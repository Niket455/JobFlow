import uuid
from typing import Any

from sqlalchemy import select

from app.models.contact import Contact
from app.repositories.base import BaseRepository


class ContactRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID, contact_id: uuid.UUID) -> Contact | None:
        return self.db.scalar(
            select(Contact).where(Contact.user_id == user_id, Contact.id == contact_id)
        )

    def list_for_user(self, user_id: uuid.UUID) -> list[Contact]:
        return list(
            self.db.scalars(
                select(Contact).where(Contact.user_id == user_id).order_by(Contact.name)
            )
        )

    def create(self, **fields: Any) -> Contact:
        contact = Contact(**fields)
        self.db.add(contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def save(self, contact: Contact) -> None:
        self.db.commit()
        self.db.refresh(contact)

    def delete(self, contact: Contact) -> None:
        self.db.delete(contact)
        self.db.commit()
