from app.gateway.base import LLMMessage, LLMResponse, LLMUsage


class MockProvider:
    """Deterministic provider for tests and local runs without an API key."""

    name = "mock"

    def __init__(self, response_text: str = "{}") -> None:
        self.response_text = response_text

    async def complete(
        self, messages: list[LLMMessage], *, model: str, temperature: float = 0.0
    ) -> LLMResponse:
        return LLMResponse(
            text=self.response_text,
            model=model,
            provider=self.name,
            usage=LLMUsage(),
        )
