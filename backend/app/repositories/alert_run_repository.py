import uuid
from typing import Any

from sqlalchemy import select

from app.models.alert_run import AlertRun
from app.repositories.base import BaseRepository


class AlertRunRepository(BaseRepository):
    def get_by_key(self, idempotency_key: str) -> AlertRun | None:
        return self.db.scalar(select(AlertRun).where(AlertRun.idempotency_key == idempotency_key))

    def list_for_alert(self, alert_id: uuid.UUID) -> list[AlertRun]:
        return list(
            self.db.scalars(
                select(AlertRun)
                .where(AlertRun.alert_id == alert_id)
                .order_by(AlertRun.created_at.desc())
            )
        )

    def create(self, **fields: Any) -> AlertRun:
        run = AlertRun(**fields)
        self.db.add(run)
        self.db.flush()
        return run
