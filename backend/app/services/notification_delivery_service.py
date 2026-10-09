from datetime import datetime

from sqlalchemy.orm import Session

from app.email.base import EmailSender
from app.models.notification import Notification
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_service import EmailDisabledError, NotificationService


class NotificationDeliveryService:
    """Emails unread, not-yet-emailed notifications as a per-user digest."""

    def __init__(
        self,
        notifications: NotificationRepository,
        users: UserRepository,
        email: NotificationService,
    ) -> None:
        self.notifications = notifications
        self.users = users
        self.email = email

    def deliver_pending(self, user: User, *, now: datetime) -> int:
        pending = self.notifications.list_pending_email(user.id)
        if not pending:
            return 0
        try:
            self.email.send(user, _subject(len(pending)), _body(pending))
        except EmailDisabledError:
            return 0
        self.notifications.mark_emailed([notification.id for notification in pending], now=now)
        return len(pending)

    def deliver_all(self, *, now: datetime, limit: int) -> int:
        delivered = 0
        for user in self.users.list_active(limit=limit):
            delivered += self.deliver_pending(user, now=now)
        return delivered


def build_notification_delivery_service(
    db: Session, sender: EmailSender
) -> NotificationDeliveryService:
    return NotificationDeliveryService(
        NotificationRepository(db), UserRepository(db), NotificationService(sender)
    )


def _subject(count: int) -> str:
    return f"You have {count} new notification{'s' if count != 1 else ''}"


def _body(notifications: list[Notification]) -> str:
    lines = ["Your latest CareerPilot notifications:", ""]
    lines.extend(f"- {notification.title}" for notification in notifications)
    return "\n".join(lines)
