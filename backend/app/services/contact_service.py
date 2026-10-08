import uuid

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text, encrypt_text
from app.models.contact import Contact
from app.models.user import User
from app.repositories.company_repository import CompanyRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.user_repository import UserRepository
from app.schemas.crm import ContactCreate, ContactRead, ContactSummary, ContactUpdate
from app.services.encryption import ensure_data_key


class ContactNotFoundError(Exception):
    pass


class UnknownCompanyError(Exception):
    pass


class ContactService:
    """User-scoped CRUD for network contacts; private notes are encrypted at rest."""

    def __init__(
        self,
        contacts: ContactRepository,
        companies: CompanyRepository,
        users: UserRepository,
    ) -> None:
        self.contacts = contacts
        self.companies = companies
        self.users = users

    def create(self, user: User, payload: ContactCreate) -> ContactRead:
        self._check_company(payload.company_id)
        data_key = ensure_data_key(user, self.users)
        contact = self.contacts.create(
            user_id=user.id,
            name=payload.name,
            title=payload.title,
            company_id=payload.company_id,
            company_name=payload.company_name,
            email=payload.email,
            phone=payload.phone,
            linkedin_url=payload.linkedin_url,
            relationship=payload.relationship,
            notes_enc=encrypt_text(data_key, payload.notes) if payload.notes else None,
        )
        return _to_read(contact, data_key)

    def update(self, user: User, contact_id: uuid.UUID, payload: ContactUpdate) -> ContactRead:
        contact = self._get(user, contact_id)
        data_key = ensure_data_key(user, self.users)
        updates = payload.model_dump(exclude_unset=True)
        if "company_id" in updates:
            self._check_company(updates["company_id"])
        if "notes" in updates:
            notes = updates.pop("notes")
            contact.notes_enc = encrypt_text(data_key, notes) if notes else None
        for key, value in updates.items():
            setattr(contact, key, value)
        self.contacts.save(contact)
        return _to_read(contact, data_key)

    def get(self, user: User, contact_id: uuid.UUID) -> ContactRead:
        data_key = ensure_data_key(user, self.users)
        return _to_read(self._get(user, contact_id), data_key)

    def list_for_user(self, user: User) -> list[ContactSummary]:
        return [
            ContactSummary.model_validate(contact)
            for contact in self.contacts.list_for_user(user.id)
        ]

    def delete(self, user: User, contact_id: uuid.UUID) -> None:
        self.contacts.delete(self._get(user, contact_id))

    def _get(self, user: User, contact_id: uuid.UUID) -> Contact:
        contact = self.contacts.get_for_user(user.id, contact_id)
        if contact is None:
            raise ContactNotFoundError
        return contact

    def _check_company(self, company_id: uuid.UUID | None) -> None:
        if company_id is not None and self.companies.get(company_id) is None:
            raise UnknownCompanyError(str(company_id))


def build_contact_service(db: Session) -> ContactService:
    return ContactService(ContactRepository(db), CompanyRepository(db), UserRepository(db))


def _to_read(contact: Contact, data_key: str) -> ContactRead:
    return ContactRead(
        id=contact.id,
        name=contact.name,
        title=contact.title,
        company_id=contact.company_id,
        company_name=contact.company_name,
        email=contact.email,
        phone=contact.phone,
        linkedin_url=contact.linkedin_url,
        relationship=contact.relationship,
        notes=decrypt_text(data_key, contact.notes_enc) if contact.notes_enc else None,
        last_contacted_at=contact.last_contacted_at,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )
