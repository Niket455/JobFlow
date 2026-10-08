import logging

from app.email.base import EmailMessage

logger = logging.getLogger(__name__)


class ConsoleEmailSender:
    """Default sender: logs the message instead of sending it (safe for dev/self-host)."""

    provider = "console"

    def send(self, message: EmailMessage) -> None:
        logger.info(
            "email (console) to=%s subject=%r\n%s", message.to, message.subject, message.text
        )
