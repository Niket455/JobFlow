from dataclasses import dataclass
from typing import Protocol


@dataclass
class EmailMessage:
    to: str
    subject: str
    text: str


class EmailError(Exception):
    pass


class EmailSender(Protocol):
    provider: str

    def send(self, message: EmailMessage) -> None: ...
