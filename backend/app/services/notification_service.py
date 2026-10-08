from app.core.config import settings
from app.email.base import EmailMessage, EmailSender
from app.models.user import User


class EmailDisabledError(Exception):
    pass


class NotificationService:
    """Sends user-facing notifications through the configured email sender."""

    def __init__(self, sender: EmailSender) -> None:
        self.sender = sender

    def send_test_email(self, user: User) -> EmailMessage:
        if not settings.email_enabled:
            raise EmailDisabledError
        message = EmailMessage(
            to=user.email,
            subject="CareerPilot test email",
            text=(
                "This is a test email from CareerPilot. "
                "If you received it, email notifications are configured correctly."
            ),
        )
        self.sender.send(message)
        return message
