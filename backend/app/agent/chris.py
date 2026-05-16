from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.agent.prompts.render import render_system_prompt
from app.agent.tools.executor import ToolExecutionContext, ToolExecutor
from app.agent.tools.registry import build_tool_executor
from app.config import get_settings
from app.domain.models import ConversationParty
from app.domain.repositories.memory import append_message
from app.domain.repositories.serialization import to_jsonable


@dataclass
class AgentTurnResult:
    turn_id: str
    system_prompt: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    outgoing_messages: list[dict[str, Any]] = field(default_factory=list)
    final_message: str = ""


class ChrisAgent:
    """Context-injected Chris runtime.

    This first build uses a deterministic scaffold policy so local development
    and prompt evals run without depending on live model calls. The LLM provider
    abstraction is implemented separately and can drive the same tool executor.
    """

    def __init__(self, tool_executor: ToolExecutor | None = None) -> None:
        self._tool_executor = tool_executor or build_tool_executor()
        self._settings = get_settings()

    def run_turn(
        self,
        db: Session,
        property_context: dict[str, Any],
        current_turn: dict[str, Any],
    ) -> AgentTurnResult:
        property_id = UUID(str(property_context["property_id"]))
        turn_id = str(uuid4())
        system_prompt = render_system_prompt(property_context, current_turn)
        result = AgentTurnResult(turn_id=turn_id, system_prompt=system_prompt)
        tool_context = ToolExecutionContext(
            db=db,
            property_id=property_id,
            turn_id=turn_id,
            sender_role=current_turn["sender_role"],
        )

        append_message(
            property_id,
            db,
            ConversationParty(current_turn["sender_role"]),
            current_turn.get("thread_id", "default"),
            {
                "role": current_turn["sender_role"],
                "body": current_turn["body"],
                "channel": current_turn["channel"],
            },
        )

        plan = self._call_tool(
            result,
            tool_context,
            "plan.review_or_create",
            {
                "plan_name": _plan_name(current_turn["body"]),
                "steps": [
                    {
                        "description": "Classify the request and authority boundary.",
                        "status": "in_progress",
                    },
                    {
                        "description": "Take the next allowed operational action.",
                        "status": "pending",
                    },
                    {
                        "description": "Record evidence and update the requester.",
                        "status": "pending",
                    },
                ],
            },
        )
        plan_id = plan.get("plan", {}).get("id")

        body = current_turn["body"].lower()
        sender_role = current_turn["sender_role"]

        if _contains_injection(body):
            self._call_tool(
                result,
                tool_context,
                "escalate",
                {
                    "reason": "Message contained instruction-like prompt injection; treated as data.",
                    "severity": "medium",
                },
            )
            self._message(
                result,
                tool_context,
                "tenant" if sender_role == "tenant" else sender_role,
                "I have noted your message and will continue using the property management rules already in place.",
            )
        elif "paid" in body or "receipt" in body:
            if sender_role == "landlord" and "confirm" in body:
                self._call_tool(
                    result,
                    tool_context,
                    "escalate",
                    {
                        "reason": "Landlord confirmed payment, but no payment_id was supplied to the scaffold agent.",
                        "severity": "low",
                    },
                )
            else:
                self._call_tool(
                    result,
                    tool_context,
                    "messaging.ask_question",
                    {
                        "to_role": "landlord",
                        "body": "Can you confirm whether the tenant payment has been received?",
                    },
                )
                result.outgoing_messages.append(
                    {
                        "to_role": "landlord",
                        "body": "Can you confirm whether the tenant payment has been received?",
                    }
                )
        elif _mentions_contractor_choice(body):
            self._call_tool(
                result,
                tool_context,
                "provider.list_preferred",
                {"trade": _infer_trade(body)},
            )
            self._call_tool(
                result,
                tool_context,
                "messaging.ask_question",
                {
                    "to_role": "landlord",
                    "body": "Which approved provider should I contact for this request?",
                },
            )
            result.outgoing_messages.append(
                {
                    "to_role": "landlord",
                    "body": "Which approved provider should I contact for this request?",
                }
            )
        else:
            self._call_tool(
                result,
                tool_context,
                "provider.list_preferred",
                {"trade": _infer_trade(body)},
            )
            self._message(
                result,
                tool_context,
                "tenant" if sender_role == "tenant" else "landlord",
                "Thanks, I have opened a plan for this and will coordinate the next step.",
            )

        if plan_id:
            self._call_tool(
                result,
                tool_context,
                "plan.mark_step",
                {
                    "plan_id": plan_id,
                    "step_index": 0,
                    "status": "done",
                    "evidence": "Authority boundary reviewed before external action.",
                },
            )
        result.final_message = "Turn completed with scoped context and recorded tool traces."
        return result

    def _call_tool(
        self,
        result: AgentTurnResult,
        context: ToolExecutionContext,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        if len(result.tool_calls) >= self._settings.APP_AGENT_TOOL_BUDGET:
            output = {"ok": False, "error": "Tool budget exhausted."}
        else:
            output = self._tool_executor.execute(context, name, arguments)
        result.tool_calls.append({"name": name, "arguments": arguments, "output": to_jsonable(output)})
        return to_jsonable(output)

    def _message(
        self,
        result: AgentTurnResult,
        context: ToolExecutionContext,
        to_role: str,
        body: str,
    ) -> None:
        self._call_tool(
            result,
            context,
            "messaging.send",
            {"to_role": to_role, "channel": "whatsapp", "body": body, "attachments": []},
        )
        result.outgoing_messages.append({"to_role": to_role, "body": body})


def _contains_injection(body: str) -> bool:
    triggers = ["ignore previous", "ignore all previous", "act as admin", "system prompt", "bypass"]
    return any(trigger in body for trigger in triggers)


def _mentions_contractor_choice(body: str) -> bool:
    return any(term in body for term in ["contractor", "provider", "plumber", "electrician"])


def _infer_trade(body: str) -> str:
    if "electric" in body:
        return "electrician"
    if "plumb" in body or "leak" in body or "water" in body:
        return "plumber"
    if "heat" in body or "boiler" in body:
        return "heating"
    return "general maintenance"


def _plan_name(body: str) -> str:
    words = " ".join(body.strip().split())[:60]
    return f"Request: {words or 'incoming message'}"
