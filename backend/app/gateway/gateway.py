import asyncio
import logging
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.gateway.base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=BaseModel)


class LLMGateway:
    """Single entry point for all provider calls.

    Owns retries/backoff, structured-output validation with a repair pass, and usage logging.
    Provider portability, caching, budgets, and PII redaction extend this class in later phases.
    """

    def __init__(self, provider: LLMProvider, *, max_retries: int = 3) -> None:
        self.provider = provider
        self.max_retries = max_retries

    async def complete(
        self, messages: list[LLMMessage], *, model: str, temperature: float = 0.0
    ) -> LLMResponse:
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.provider.complete(
                    messages, model=model, temperature=temperature
                )
            except Exception as exc:  # noqa: BLE001 — provider errors are retried uniformly
                last_exc = exc
                logger.warning(
                    "llm provider error (attempt %s/%s): %s", attempt, self.max_retries, exc
                )
                await asyncio.sleep(min(2 ** (attempt - 1), 8))
            else:
                logger.info(
                    "llm call provider=%s model=%s prompt_tokens=%s completion_tokens=%s",
                    response.provider,
                    response.model,
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                )
                return response
        assert last_exc is not None
        raise last_exc

    async def complete_structured(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        schema: type[ModelT],
        temperature: float = 0.0,
    ) -> ModelT:
        response = await self.complete(messages, model=model, temperature=temperature)
        try:
            return schema.model_validate_json(response.text)
        except ValidationError as exc:
            repair = [
                *messages,
                LLMMessage(
                    role="user",
                    content=(
                        "Your previous reply was not valid JSON for the required schema. "
                        f"Return ONLY valid JSON. Validation error: {exc}"
                    ),
                ),
            ]
            repaired = await self.complete(repair, model=model, temperature=0.0)
            return schema.model_validate_json(repaired.text)
