from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class InboundEmail:
    external_id: str
    sender: str
    subject: str
    snippet: str
    received_at: datetime


class InboxError(Exception):
    pass


class InboxNotConfiguredError(InboxError):
    pass


class InboxProvider(Protocol):
    provider: str

    def fetch(self, *, since: datetime | None) -> list[InboundEmail]: ...
