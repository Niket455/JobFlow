import uuid
from typing import Any

from sqlalchemy import select

from app.models.application_event import ApplicationEvent
from app.repositories.base import BaseRepository


class ApplicationEventRepository(BaseRepository):
    def create(self, **fields: Any) -> ApplicationEvent:
        event = ApplicationEvent(**fields)
        self.db.add(event)
        self.db.flush()
        return event

    def list_for_application(self, application_id: uuid.UUID) -> list[ApplicationEvent]:
        return list(
            self.db.scalars(
                select(ApplicationEvent)
                .where(ApplicationEvent.application_id == application_id)
                .order_by(ApplicationEvent.occurred_at, ApplicationEvent.created_at)
            )
        )

    def list_for_applications(
        self, application_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[ApplicationEvent]]:
        if not application_ids:
            return {}
        rows = self.db.scalars(
            select(ApplicationEvent)
            .where(ApplicationEvent.application_id.in_(application_ids))
            .order_by(ApplicationEvent.occurred_at, ApplicationEvent.created_at)
        )
        grouped: dict[uuid.UUID, list[ApplicationEvent]] = {}
        for row in rows:
            grouped.setdefault(row.application_id, []).append(row)
        return grouped
