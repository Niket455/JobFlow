from app.core.config import Settings, settings
from app.integrations.base import InboxProvider
from app.integrations.gmail import GmailInboxProvider
from app.integrations.mock_inbox import MockInboxProvider


def build_inbox_provider(provider: str, config: Settings = settings) -> InboxProvider:
    if provider == "mock":
        return MockInboxProvider()
    if provider == "gmail":
        return GmailInboxProvider()
    raise ValueError(f"Unknown inbox provider: {provider}")
