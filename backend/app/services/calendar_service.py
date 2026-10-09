import uuid

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.calendar_suggestion_repository import CalendarSuggestionRepository
from app.schemas.integrations import CalendarCreate, CalendarRead


class CalendarSuggestionNotFoundError(Exception):
    pass


class CalendarService:
    """Confirm-to-add calendar suggestions.

    Confirming only records the decision (no external calendar write).
    """

    def __init__(self, suggestions: CalendarSuggestionRepository) -> None:
        self.suggestions = suggestions

    def list_for_user(self, user: User) -> list[CalendarRead]:
        return [
            CalendarRead.model_validate(suggestion)
            for suggestion in self.suggestions.list_for_user(user.id)
        ]

    def create(self, user: User, payload: CalendarCreate) -> CalendarRead:
        suggestion = self.suggestions.create(
            user_id=user.id,
            application_id=payload.application_id,
            email_message_id=None,
            kind=payload.kind,
            title=payload.title,
            proposed_at=payload.proposed_at,
            notes=payload.notes,
            status="suggested",
        )
        return CalendarRead.model_validate(suggestion)

    def confirm(self, user: User, suggestion_id: uuid.UUID) -> CalendarRead:
        return self._set_status(user, suggestion_id, "confirmed")

    def dismiss(self, user: User, suggestion_id: uuid.UUID) -> CalendarRead:
        return self._set_status(user, suggestion_id, "dismissed")

    def _set_status(self, user: User, suggestion_id: uuid.UUID, status: str) -> CalendarRead:
        suggestion = self.suggestions.get_for_user(user.id, suggestion_id)
        if suggestion is None:
            raise CalendarSuggestionNotFoundError
        suggestion.status = status
        self.suggestions.save(suggestion)
        return CalendarRead.model_validate(suggestion)


def build_calendar_service(db: Session) -> CalendarService:
    return CalendarService(CalendarSuggestionRepository(db))
