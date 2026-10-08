import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.models.alert import Alert
from app.repositories.base import BaseRepository


class AlertRepository(BaseRepository):
    def get_for_user(self, user_id: uuid.UUID, alert_id: uuid.UUID) -> Alert | None:
        return self.db.scalar(select(Alert).where(Alert.user_id == user_id, Alert.id == alert_id))

    def get_by_token(self, token: str) -> Alert | None:
        return self.db.scalar(select(Alert).where(Alert.unsubscribe_token == token))

    def list_for_user(self, user_id: uuid.UUID) -> list[Alert]:
        return list(
            self.db.scalars(
                select(Alert).where(Alert.user_id == user_id).order_by(Alert.created_at)
            )
        )

    def list_due(self, due_before: datetime, *, limit: int) -> list[Alert]:
        return list(
            self.db.scalars(
                select(Alert)
                .where(
                    Alert.enabled.is_(True),
                    Alert.next_run_at.is_not(None),
                    Alert.next_run_at <= due_before,
                )
                .order_by(Alert.next_run_at)
                .limit(limit)
            )
        )

    def create(self, **fields: Any) -> Alert:
        alert = Alert(**fields)
        self.db.add(alert)
        self.db.flush()
        return alert

    def save(self, alert: Alert) -> None:
        self.db.commit()
        self.db.refresh(alert)

    def delete(self, alert: Alert) -> None:
        self.db.delete(alert)
