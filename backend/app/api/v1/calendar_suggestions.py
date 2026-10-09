import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.integrations import CalendarCreate, CalendarRead
from app.services.calendar_service import (
    CalendarSuggestionNotFoundError,
    build_calendar_service,
)

router = APIRouter(prefix="/calendar-suggestions", tags=["calendar"])


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Calendar suggestion not found"
    )


@router.post("", response_model=CalendarRead, status_code=status.HTTP_201_CREATED)
def create_calendar_suggestion(
    payload: CalendarCreate, current_user: CurrentUser, db: DbSession
) -> CalendarRead:
    return build_calendar_service(db).create(current_user, payload)


@router.get("", response_model=list[CalendarRead])
def list_calendar_suggestions(current_user: CurrentUser, db: DbSession) -> list[CalendarRead]:
    return build_calendar_service(db).list_for_user(current_user)


@router.post("/{suggestion_id}/confirm", response_model=CalendarRead)
def confirm_calendar_suggestion(
    suggestion_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> CalendarRead:
    try:
        return build_calendar_service(db).confirm(current_user, suggestion_id)
    except CalendarSuggestionNotFoundError as exc:
        raise _not_found() from exc


@router.post("/{suggestion_id}/dismiss", response_model=CalendarRead)
def dismiss_calendar_suggestion(
    suggestion_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> CalendarRead:
    try:
        return build_calendar_service(db).dismiss(current_user, suggestion_id)
    except CalendarSuggestionNotFoundError as exc:
        raise _not_found() from exc
