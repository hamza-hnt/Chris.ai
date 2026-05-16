from typing import Any

from openai import OpenAI

from app.agent.providers.base import LLMMessage, LLMProvider, LLMResponse, LLMToolCall
from app.config import Settings


class OpenAIProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())

    def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
        tool_budget: int,
    ) -> LLMResponse:
        response = self._client.chat.completions.create(
            model=self._settings.OPENAI_MODEL,
            messages=[{"role": message.role, "content": message.content} for message in messages],
            tools=[_to_openai_tool(schema) for schema in tools],
            tool_choice="auto",
            max_completion_tokens=1000,
        )
        choice = response.choices[0].message
        tool_calls = [
            LLMToolCall(name=call.function.name, arguments=_json_arguments(call.function.arguments))
            for call in choice.tool_calls or []
        ][:tool_budget]
        return LLMResponse(content=choice.content, tool_calls=tool_calls)


def _to_openai_tool(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": schema["name"],
            "description": schema["description"],
            "parameters": schema["parameters"],
        },
    }


def _json_arguments(raw: str) -> dict[str, Any]:
    import json

    if not raw:
        return {}
    return json.loads(raw)
