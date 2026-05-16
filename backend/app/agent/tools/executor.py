import time
from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.repositories.memory import record_tool_trace


ToolHandler = Callable[["ToolExecutionContext", dict[str, Any]], dict[str, Any]]


@dataclass
class ToolExecutionContext:
    db: Session
    property_id: UUID
    turn_id: str
    sender_role: str


class ToolExecutor:
    def __init__(self, handlers: dict[str, ToolHandler]) -> None:
        self._handlers = handlers

    @property
    def names(self) -> list[str]:
        return sorted(self._handlers)

    def execute(
        self,
        context: ToolExecutionContext,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        if tool_name not in self._handlers:
            output = {"ok": False, "error": f"Unknown tool: {tool_name}"}
            record_tool_trace(
                context.property_id,
                context.db,
                context.turn_id,
                tool_name,
                arguments,
                output,
                0,
            )
            return output

        started = time.perf_counter()
        try:
            output = self._handlers[tool_name](context, arguments)
        except Exception as exc:
            output = {"ok": False, "error": str(exc), "refused": True}
        duration_ms = int((time.perf_counter() - started) * 1000)
        record_tool_trace(
            context.property_id,
            context.db,
            context.turn_id,
            tool_name,
            arguments,
            output,
            duration_ms,
        )
        return output
