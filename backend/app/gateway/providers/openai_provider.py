from typing import cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.gateway.base import LLMMessage, LLMResponse, LLMUsage


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str, timeout: float = 30.0) -> None:
        self._client = AsyncOpenAI(api_key=api_key, timeout=timeout)

    async def complete(
        self, messages: list[LLMMessage], *, model: str, temperature: float = 0.0
    ) -> LLMResponse:
        chat_messages = [
            cast(ChatCompletionMessageParam, {"role": message.role, "content": message.content})
            for message in messages
        ]
        result = await self._client.chat.completions.create(
            model=model, messages=chat_messages, temperature=temperature
        )
        usage = result.usage
        return LLMResponse(
            text=result.choices[0].message.content or "",
            model=result.model,
            provider=self.name,
            usage=LLMUsage(
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            ),
        )
