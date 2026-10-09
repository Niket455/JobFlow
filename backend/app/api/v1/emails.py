import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.integrations import EmailRead, EmailSuggestion
from app.services.email_service import (
    EmailMessageNotFoundError,
    EmailNotActionableError,
    build_email_service,
)

router = APIRouter(prefix="/emails", tags=["emails"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")


@router.get("", response_model=list[EmailRead])
def list_emails(
    current_user: CurrentUser,
    db: DbSession,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[EmailRead]:
    return build_email_service(db).list_for_user(current_user, status=status_filter)


@router.get("/{message_id}", response_model=EmailRead)
def get_email(message_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> EmailRead:
    try:
        return build_email_service(db).get(current_user, message_id)
    except EmailMessageNotFoundError as exc:
        raise _not_found() from exc


@router.post("/{message_id}/suggest", response_model=EmailSuggestion)
def suggest_email(
    message_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> EmailSuggestion:
    try:
        return build_email_service(db).suggest(current_user, message_id)
    except EmailMessageNotFoundError as exc:
        raise _not_found() from exc


@router.post("/{message_id}/accept", response_model=EmailRead)
def accept_email(message_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> EmailRead:
    try:
        return build_email_service(db).accept(current_user, message_id)
    except EmailMessageNotFoundError as exc:
        raise _not_found() from exc
    except EmailNotActionableError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is not linked to an application or suggests no status change",
        ) from exc


@router.post("/{message_id}/dismiss", response_model=EmailRead)
def dismiss_email(message_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> EmailRead:
    try:
        return build_email_service(db).dismiss(current_user, message_id)
    except EmailMessageNotFoundError as exc:
        raise _not_found() from exc
