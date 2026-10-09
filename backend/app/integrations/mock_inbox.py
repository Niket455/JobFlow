from datetime import UTC, datetime

from app.integrations.base import InboundEmail

# A small, deterministic inbox so sync works offline (dev/tests/smoke).
DEFAULT_MESSAGES: list[InboundEmail] = [
    InboundEmail(
        external_id="msg-ack",
        sender="no-reply@acme.com",
        subject="We received your application",
        snippet="Thanks for applying to the Data Engineer role. We'll be in touch.",
        received_at=datetime(2026, 1, 2, 9, 0, tzinfo=UTC),
    ),
    InboundEmail(
        external_id="msg-interview",
        sender="recruiting@acme.com",
        subject="Interview invitation — Data Engineer",
        snippet="We'd like to schedule an interview for the Data Engineer position next week.",
        received_at=datetime(2026, 1, 4, 15, 30, tzinfo=UTC),
    ),
    InboundEmail(
        external_id="msg-news",
        sender="news@example.com",
        subject="Weekly engineering newsletter",
        snippet="Top stories in software engineering this week.",
        received_at=datetime(2026, 1, 5, 7, 0, tzinfo=UTC),
    ),
]


class MockInboxProvider:
    """Offline inbox provider returning a fixed, reproducible set of messages."""

    provider = "mock"

    def __init__(self, messages: list[InboundEmail] | None = None) -> None:
        self._messages = list(messages) if messages is not None else list(DEFAULT_MESSAGES)

    def fetch(self, *, since: datetime | None) -> list[InboundEmail]:
        if since is None:
            return list(self._messages)
        return [message for message in self._messages if message.received_at > since]
