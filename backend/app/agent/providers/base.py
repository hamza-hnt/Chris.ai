from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


MessageRole = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True)
class LLMMessage:
    role: MessageRole
    content: str


@dataclass(frozen=True)
class LLMToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    content: str | None = None
    tool_calls: list[LLMToolCall] = field(default_factory=list)


class LLMProvider(ABC):
    @abstractmethod
    def complete(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
        tool_budget: int,
    ) -> LLMResponse:
        """Return an assistant response or tool calls."""
