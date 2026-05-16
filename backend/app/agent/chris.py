import json
import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from agents import Agent, FunctionTool, ModelSettings, Runner
from sqlalchemy.orm import Session

from app.agent.providers.base import LLMProvider
from app.agent.prompts.render import render_system_prompt
from app.agent.tools.executor import ToolExecutionContext, ToolExecutor
from app.agent.tools.registry import build_tool_executor
from app.agent.tools.schemas import TOOL_SCHEMAS
from app.config import get_settings
from app.domain.models import ConversationParty
from app.domain.repositories.memory import append_message
from app.domain.repositories.serialization import to_jsonable


AGENT_SDK_MODEL = "gpt-5.4-mini"


@dataclass
class AgentTurnResult:
    turn_id: str
    system_prompt: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    outgoing_messages: list[dict[str, Any]] = field(default_factory=list)
    final_message: str = ""


class ChrisAgent:
    """Context-injected Chris runtime.

    The deterministic runtime is kept for prompt evals and local tests. In
    normal dev/prod use, APP_AGENT_RUNTIME=llm routes decisions through the
    OpenAI Agents SDK while every tool execution remains property-scoped.
    """

    def __init__(
        self,
        tool_executor: ToolExecutor | None = None,
        provider: LLMProvider | None = None,
    ) -> None:
        self._tool_executor = tool_executor or build_tool_executor()
        self._settings = get_settings()
        self._provider = provider

    def run_turn(
        self,
        db: Session,
        property_context: dict[str, Any],
        current_turn: dict[str, Any],
    ) -> AgentTurnResult:
        if self._settings.APP_AGENT_RUNTIME == "llm":
            return self._run_llm_turn(db, property_context, current_turn)
        return self._run_deterministic_turn(db, property_context, current_turn)

    def _run_deterministic_turn(
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

    def _run_llm_turn(
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

        agent = Agent(
            name="Chris Property Manager",
            instructions=_agent_sdk_instructions(system_prompt),
            model=AGENT_SDK_MODEL,
            model_settings=ModelSettings(
                parallel_tool_calls=False,
                max_tokens=1000,
            ),
            tools=self._agent_sdk_tools(result, tool_context),
            tool_use_behavior="run_llm_again",
        )
        run_result = _run_agent_sync(
            agent,
            _agent_sdk_input(current_turn, plan),
            max_turns=max(2, min(self._settings.APP_AGENT_TOOL_BUDGET, 12)),
        )
        content = str(run_result.final_output or "").strip()
        if content:
            result.final_message = content
            if not result.outgoing_messages:
                self._message(
                    result,
                    tool_context,
                    _reply_role(current_turn["sender_role"]),
                    content,
                )
        if not result.final_message:
            result.final_message = "Turn completed through OpenAI Agents SDK runtime."
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

    def _record_outgoing_from_tool(
        self,
        result: AgentTurnResult,
        name: str,
        arguments: dict[str, Any],
        output: dict[str, Any],
    ) -> None:
        if not name.startswith("messaging."):
            return
        message = output.get("message", {}) if output.get("ok") is True else {}
        body = arguments.get("body") or message.get("body")
        to_role = arguments.get("to_role") or message.get("to_role")
        if body and to_role:
            result.outgoing_messages.append({"to_role": to_role, "body": body})

    def _agent_sdk_tools(
        self,
        result: AgentTurnResult,
        context: ToolExecutionContext,
    ) -> list[FunctionTool]:
        tools = []
        for schema in TOOL_SCHEMAS:
            tool_name = schema["name"]
            if tool_name == "plan.review_or_create":
                continue
            tools.append(
                FunctionTool(
                    name=_sdk_tool_name(tool_name),
                    description=schema["description"],
                    params_json_schema=schema["parameters"],
                    on_invoke_tool=_build_sdk_tool_handler(self, result, context, tool_name),
                    strict_json_schema=False,
                )
            )
        return tools


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


def _reply_role(sender_role: str) -> str:
    return sender_role if sender_role in {"tenant", "landlord", "provider"} else "tenant"


def _json_dump(value: Any) -> str:
    return json.dumps(to_jsonable(value), indent=2, sort_keys=True)


def _agent_sdk_instructions(system_prompt: str) -> str:
    return (
        f"{system_prompt}\n\n"
        "---\n\n"
        "# Agentic Runtime Contract\n\n"
        "You are running inside the OpenAI Agents SDK. Think through the work in "
        "private, but never expose hidden reasoning to the user.\n\n"
        "For each turn, privately do this loop:\n"
        "1. Understand the user's real objective.\n"
        "2. Check the provided property context, active plans, recent actions, and tool traces.\n"
        "3. Decide whether a direct reply is enough or a tool is needed.\n"
        "4. Maintain a small action plan using the plan tools already available.\n"
        "5. Execute only the next useful step, avoiding duplicated actions already present in context.\n"
        "6. Use Tavily-backed `provider__search` when a nearby outside provider shortlist is needed.\n"
        "7. Ask one concise question only when required information is genuinely missing.\n\n"
        "The first `plan.review_or_create` call has already been executed by the application "
        "before this run. Continue from that plan state. Use tools for externally visible "
        "actions. If the current sender is the tenant, send the tenant a brief acknowledgement "
        "or status update even when the next approval question must go to the landlord.\n\n"
        "Final output must be short and operational: say what was done, what is pending, "
        "or the next action. Do not include chain-of-thought."
    )


def _agent_sdk_input(current_turn: dict[str, Any], initial_plan: dict[str, Any]) -> str:
    return (
        "Continue this Chris.AI property-management turn.\n\n"
        f"Current turn:\n```json\n{_json_dump(current_turn)}\n```\n\n"
        f"Initial plan tool result:\n```json\n{_json_dump(initial_plan)}\n```"
    )


def _build_sdk_tool_handler(
    agent: ChrisAgent,
    result: AgentTurnResult,
    context: ToolExecutionContext,
    tool_name: str,
):
    async def invoke(_ctx, raw_arguments: str) -> str:
        arguments = json.loads(raw_arguments or "{}")
        output = agent._call_tool(result, context, tool_name, arguments)
        agent._record_outgoing_from_tool(result, tool_name, arguments, output)
        return _json_dump(output)

    return invoke


def _sdk_tool_name(name: str) -> str:
    return name.replace(".", "__")


def _run_agent_sync(agent: Agent, input_text: str, max_turns: int):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return Runner.run_sync(agent, input_text, max_turns=max_turns)

    holder: dict[str, Any] = {}

    def run_in_thread() -> None:
        try:
            holder["result"] = Runner.run_sync(agent, input_text, max_turns=max_turns)
        except BaseException as exc:
            holder["error"] = exc

    thread = threading.Thread(target=run_in_thread, name="chris-agent-sdk-runner")
    thread.start()
    thread.join()
    if "error" in holder:
        raise holder["error"]
    return holder["result"]
