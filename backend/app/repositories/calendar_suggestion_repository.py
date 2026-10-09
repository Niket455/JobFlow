import uuid
from typing import Any

from sqlalchemy import select

from app.models.calendar_suggestion import CalendarSuggestion
from app.repositories.base import BaseRepository


class CalendarSuggestionRepository(BaseRepository):
    def get_for_user(
        self, user_id: uuid.UUID, suggestion_id: uuid.UUID
    ) -> CalendarSuggestion | None:
        return self.db.scalar(
            select(CalendarSuggestion).where(
                CalendarSuggestion.user_id == user_id,
                CalendarSuggestion.id == suggestion_id,
            )
        )

    def list_for_user(self, user_id: uuid.UUID) -> list[CalendarSuggestion]:
        return list(
            self.db.scalars(
                select(CalendarSuggestion)
                .where(CalendarSuggestion.user_id == user_id)
                .order_by(CalendarSuggestion.created_at.desc())
            )
        )

    def create(self, **fields: Any) -> CalendarSuggestion:
        suggestion = CalendarSuggestion(**fields)
        self.db.add(suggestion)
        self.db.commit()
        self.db.refresh(suggestion)
        return suggestion

    def save(self, suggestion: CalendarSuggestion) -> None:
        self.db.commit()
        self.db.refresh(suggestion)
