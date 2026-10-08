from dataclasses import dataclass, field

from app.email.base import EmailMessage


@dataclass
class RecordingEmailSender:
    """In-memory sandbox sender: records messages in `outbox` instead of sending them."""

    provider: str = "recording"
    outbox: list[EmailMessage] = field(default_factory=list)

    def send(self, message: EmailMessage) -> None:
        self.outbox.append(message)
