from datetime import datetime

from app.integrations.base import InboundEmail, InboxNotConfiguredError


class GmailInboxProvider:
    """Read-only Gmail inbox provider — a stub until OAuth credentials + client exist."""

    provider = "gmail"

    def fetch(self, *, since: datetime | None) -> list[InboundEmail]:
        raise InboxNotConfiguredError("Gmail integration is not configured (OAuth not implemented)")
