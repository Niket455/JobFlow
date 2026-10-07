import asyncio

import pytest
from pydantic import BaseModel

from app.gateway.base import LLMMessage, LLMResponse, LLMUsage
from app.gateway.gateway import LLMGateway
from app.gateway.providers.mock_provider import MockProvider


class _Answer(BaseModel):
    summary: str
    score: int


class _SequenceProvider:
    name = "sequence"

    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self.calls = 0

    async def complete(
        self, messages: list[LLMMessage], *, model: str, temperature: float = 0.0
    ) -> LLMResponse:
        text = self._responses[min(self.calls, len(self._responses) - 1)]
        self.calls += 1
        return LLMResponse(text=text, model=model, provider=self.name, usage=LLMUsage())


class _FlakyProvider:
    name = "flaky"

    def __init__(self) -> None:
        self.calls = 0

    async def complete(
        self, messages: list[LLMMessage], *, model: str, temperature: float = 0.0
    ) -> LLMResponse:
        self.calls += 1
        if self.calls < 2:
            raise RuntimeError("transient provider error")
        return LLMResponse(text="ok", model=model, provider=self.name, usage=LLMUsage())


def test_gateway_returns_text() -> None:
    gateway = LLMGateway(MockProvider("hello"), max_retries=1)
    response = asyncio.run(gateway.complete([], model="mock-1"))
    assert response.text == "hello"
    assert response.provider == "mock"


def test_gateway_structured_valid() -> None:
    gateway = LLMGateway(MockProvider('{"summary": "good fit", "score": 8}'), max_retries=1)
    result = asyncio.run(gateway.complete_structured([], model="mock-1", schema=_Answer))
    assert result.summary == "good fit"
    assert result.score == 8


def test_gateway_repairs_invalid_json() -> None:
    provider = _SequenceProvider(["not json", '{"summary": "ok", "score": 5}'])
    gateway = LLMGateway(provider, max_retries=1)
    result = asyncio.run(gateway.complete_structured([], model="mock-1", schema=_Answer))
    assert result.score == 5
    assert provider.calls == 2


def test_gateway_retries_transient_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    provider = _FlakyProvider()
    gateway = LLMGateway(provider, max_retries=3)
    response = asyncio.run(gateway.complete([], model="mock-1"))
    assert response.text == "ok"
    assert provider.calls == 2
