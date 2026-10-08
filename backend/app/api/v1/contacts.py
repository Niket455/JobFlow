import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.crm import ContactCreate, ContactRead, ContactSummary, ContactUpdate
from app.services.contact_service import (
    ContactNotFoundError,
    UnknownCompanyError,
    build_contact_service,
)

router = APIRouter(prefix="/contacts", tags=["contacts"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")


@router.post("", response_model=ContactRead, status_code=status.HTTP_201_CREATED)
def create_contact(payload: ContactCreate, current_user: CurrentUser, db: DbSession) -> ContactRead:
    try:
        return build_contact_service(db).create(current_user, payload)
    except UnknownCompanyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown company"
        ) from exc


@router.get("", response_model=list[ContactSummary])
def list_contacts(current_user: CurrentUser, db: DbSession) -> list[ContactSummary]:
    return build_contact_service(db).list_for_user(current_user)


@router.get("/{contact_id}", response_model=ContactRead)
def get_contact(contact_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> ContactRead:
    try:
        return build_contact_service(db).get(current_user, contact_id)
    except ContactNotFoundError as exc:
        raise _not_found() from exc


@router.put("/{contact_id}", response_model=ContactRead)
def update_contact(
    contact_id: uuid.UUID, payload: ContactUpdate, current_user: CurrentUser, db: DbSession
) -> ContactRead:
    try:
        return build_contact_service(db).update(current_user, contact_id, payload)
    except ContactNotFoundError as exc:
        raise _not_found() from exc
    except UnknownCompanyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown company"
        ) from exc


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(contact_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> None:
    try:
        build_contact_service(db).delete(current_user, contact_id)
    except ContactNotFoundError as exc:
        raise _not_found() from exc
