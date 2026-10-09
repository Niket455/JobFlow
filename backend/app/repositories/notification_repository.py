import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository):
    def exists(self, user_id: uuid.UUID, dedupe_key: str) -> bool:
        found = self.db.scalar(
            select(Notification.id)
            .where(Notification.user_id == user_id, Notification.dedupe_key == dedupe_key)
            .limit(1)
        )
        return found is not None

    def get_for_user(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification | None:
        return self.db.scalar(
            select(Notification).where(
                Notification.user_id == user_id, Notification.id == notification_id
            )
        )

    def list_for_user(
        self, user_id: uuid.UUID, *, unread_only: bool = False, limit: int = 100
    ) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        return list(self.db.scalars(query.order_by(Notification.created_at.desc()).limit(limit)))

    def unread_count(self, user_id: uuid.UUID) -> int:
        count = self.db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        )
        return int(count or 0)

    def list_pending_email(self, user_id: uuid.UUID, *, limit: int = 100) -> list[Notification]:
        return list(
            self.db.scalars(
                select(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                    Notification.emailed_at.is_(None),
                )
                .order_by(Notification.created_at)
                .limit(limit)
            )
        )

    def mark_emailed(self, ids: list[uuid.UUID], *, now: datetime) -> None:
        if not ids:
            return
        self.db.execute(update(Notification).where(Notification.id.in_(ids)).values(emailed_at=now))
        self.db.commit()

    def create(self, **fields: Any) -> Notification:
        notification = Notification(**fields)
        self.db.add(notification)
        self.db.flush()
        return notification

    def save(self, notification: Notification) -> None:
        self.db.commit()
        self.db.refresh(notification)

    def delete(self, notification: Notification) -> None:
        self.db.delete(notification)
        self.db.commit()

    def mark_all_read(self, user_id: uuid.UUID, *, now: datetime) -> int:
        result = self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=now)
        )
        self.db.commit()
        return int(getattr(result, "rowcount", 0) or 0)
