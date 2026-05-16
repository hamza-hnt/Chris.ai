from app.agent.providers.base import LLMMessage, LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict],
        tool_budget: int,
    ) -> LLMResponse:
        raise NotImplementedError("AnthropicProvider is wired but not implemented in this build.")
