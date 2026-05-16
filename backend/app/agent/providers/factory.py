from app.agent.providers.anthropic_provider import AnthropicProvider
from app.agent.providers.base import LLMProvider
from app.agent.providers.openai_provider import OpenAIProvider
from app.config import Settings


def build_provider(settings: Settings) -> LLMProvider:
    if settings.LLM_PROVIDER == "openai":
        return OpenAIProvider(settings)
    if settings.LLM_PROVIDER == "anthropic":
        return AnthropicProvider()
    raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")
