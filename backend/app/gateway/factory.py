from app.core.config import Settings, settings
from app.gateway.base import LLMProvider
from app.gateway.gateway import LLMGateway
from app.gateway.providers.mock_provider import MockProvider
from app.gateway.providers.openai_provider import OpenAIProvider


def build_provider(config: Settings = settings) -> LLMProvider:
    if config.llm_provider == "mock":
        return MockProvider()
    if config.llm_provider == "openai":
        if not config.openai_api_key:
            raise RuntimeError("CAREERPILOT_OPENAI_API_KEY is required for the openai provider")
        return OpenAIProvider(config.openai_api_key, timeout=config.llm_request_timeout_seconds)
    raise ValueError(f"Unknown LLM provider: {config.llm_provider}")


def build_gateway(config: Settings = settings) -> LLMGateway:
    return LLMGateway(build_provider(config), max_retries=config.llm_max_retries)
