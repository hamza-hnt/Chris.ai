import json
import asyncio
import re
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
from app.domain.repositories.memory import append_action, append_message
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
        if _is_landlord_provider_approval_turn(current_turn) or _is_landlord_supplied_provider_turn(
            current_turn
        ):
            append_action(
                property_id,
                db,
                "landlord.approval",
                {
                    "approval": "landlord_provider_coordination",
                    "message": current_turn["body"],
                    "channel": current_turn["channel"],
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
        self._ensure_landlord_contact_when_needed(result, tool_context, property_context, current_turn)
        self._ensure_landlord_supplied_provider_contacted(
            result,
            tool_context,
            property_context,
            current_turn,
        )
        self._ensure_provider_contact_after_landlord_approval(
            result,
            tool_context,
            property_context,
            current_turn,
        )
        self._ensure_tenant_updated_after_provider_contact(result, tool_context, current_turn)
        self._ensure_provider_response_relayed(result, tool_context, property_context, current_turn)
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

    def _ensure_landlord_contact_when_needed(
        self,
        result: AgentTurnResult,
        context: ToolExecutionContext,
        property_context: dict[str, Any],
        current_turn: dict[str, Any],
    ) -> None:
        if not _should_force_landlord_contact(result, current_turn):
            return

        trade = _infer_trade(current_turn.get("body", ""))
        preferred = _matching_preferred_provider(property_context, trade)
        search = None
        if preferred is None:
            search = self._call_tool(
                result,
                context,
                "provider.search",
                {"trade": trade, "area": None, "constraints": ""},
            )
        body = _landlord_repair_approval_question(
            property_context,
            current_turn,
            trade=trade,
            preferred_provider=preferred,
            search_output=search,
        )
        output = self._call_tool(
            result,
            context,
            "messaging.ask_question",
            {"to_role": "landlord", "body": body},
        )
        self._record_outgoing_from_tool(
            result,
            "messaging.ask_question",
            {"to_role": "landlord", "body": body},
            output,
        )

    def _ensure_landlord_supplied_provider_contacted(
        self,
        result: AgentTurnResult,
        context: ToolExecutionContext,
        property_context: dict[str, Any],
        current_turn: dict[str, Any],
    ) -> None:
        if not _is_landlord_supplied_provider_turn(current_turn):
            return
        if _has_successful_tool_call(result, "provider.contact"):
            return

        body = str(current_turn.get("body", ""))
        phone = _extract_landlord_phone(body)
        email = _extract_landlord_email(body)
        trade = _infer_trade(_request_text(property_context, current_turn))
        registered = self._call_tool(
            result,
            context,
            "provider.register_contact",
            {
                "name": _extract_landlord_provider_name(body),
                "trade": trade,
                "phone": phone,
                "email": email,
                "note": "Provider contact supplied by the landlord during approval.",
            },
        )
        provider_id = registered.get("provider", {}).get("id")
        if not provider_id:
            return

        output = self._call_tool(
            result,
            context,
            "provider.contact",
            {"provider_id": provider_id, "brief": _provider_repair_brief(property_context, current_turn)},
        )
        if output.get("ok") and not _has_outgoing_role(result, "tenant"):
            provider_name = output.get("provider", {}).get("name", "le prestataire indique")
            self._message(
                result,
                context,
                "tenant",
                (
                    f"Le proprietaire m'a donne le contact de {provider_name}. "
                    "Je l'ai contacte et je vous confirme le creneau des qu'il repond."
                ),
            )

    def _ensure_provider_contact_after_landlord_approval(
        self,
        result: AgentTurnResult,
        context: ToolExecutionContext,
        property_context: dict[str, Any],
        current_turn: dict[str, Any],
    ) -> None:
        if not _should_force_provider_contact(result, property_context, current_turn):
            return

        trade = _infer_trade(_request_text(property_context, current_turn))
        provider_id = _preferred_provider_id(property_context, trade)
        if provider_id is None:
            search = self._call_tool(
                result,
                context,
                "provider.search",
                {"trade": trade, "area": None, "constraints": ""},
            )
            provider_id = _first_search_provider_id(search)
        if provider_id is None:
            return

        brief = _provider_repair_brief(property_context, current_turn)
        output = self._call_tool(
            result,
            context,
            "provider.contact",
            {"provider_id": provider_id, "brief": brief},
        )
        if output.get("ok") and not _has_outgoing_role(result, "tenant"):
            provider_name = output.get("provider", {}).get("name", "le prestataire")
            self._message(
                result,
                context,
                "tenant",
                (
                    f"Le proprietaire a donne son accord. J'ai contacte {provider_name} "
                    "et je vous confirme le creneau des que le prestataire repond."
                ),
            )

    def _ensure_tenant_updated_after_provider_contact(
        self,
        result: AgentTurnResult,
        context: ToolExecutionContext,
        current_turn: dict[str, Any],
    ) -> None:
        if not (
            _is_landlord_provider_approval_turn(current_turn)
            or _is_landlord_supplied_provider_turn(current_turn)
        ):
            return
        if not _has_successful_tool_call(result, "provider.contact"):
            return
        if _has_outgoing_role(result, "tenant"):
            return
        self._message(
            result,
            context,
            "tenant",
            (
                "Le proprietaire a donne son accord. J'ai contacte le prestataire "
                "et je vous confirme le creneau des qu'il repond."
            ),
        )

    def _ensure_provider_response_relayed(
        self,
        result: AgentTurnResult,
        context: ToolExecutionContext,
        property_context: dict[str, Any],
        current_turn: dict[str, Any],
    ) -> None:
        if current_turn.get("sender_role") != "provider":
            return
        if _has_outgoing_role(result, "tenant") or _has_outgoing_role(result, "landlord"):
            return

        body = " ".join(str(current_turn.get("body", "")).strip().split())
        if not body:
            return
        if _mentions_quote_or_cost(body):
            output = self._call_tool(
                result,
                context,
                "messaging.ask_question",
                {
                    "to_role": "landlord",
                    "body": (
                        "Le prestataire a repondu avec un element de cout ou de devis: "
                        f"{body}. Confirmez-vous que je peux continuer avec lui ?"
                    ),
                },
            )
            self._record_outgoing_from_tool(
                result,
                "messaging.ask_question",
                {"to_role": "landlord", "body": output.get("message", {}).get("body", "")},
                output,
            )
            return

        output = self._call_tool(
            result,
            context,
            "messaging.ask_question",
            {
                "to_role": "tenant",
                "body": (
                    "Le prestataire propose la suite suivante: "
                    f"{body}. Est-ce que ce creneau ou cette proposition vous convient ?"
                ),
            },
        )
        self._record_outgoing_from_tool(
            result,
            "messaging.ask_question",
            {"to_role": "tenant", "body": output.get("message", {}).get("body", "")},
            output,
        )


def _contains_injection(body: str) -> bool:
    triggers = ["ignore previous", "ignore all previous", "act as admin", "system prompt", "bypass"]
    return any(trigger in body for trigger in triggers)


def _mentions_contractor_choice(body: str) -> bool:
    return any(term in body for term in ["contractor", "provider", "plumber", "electrician"])


def _infer_trade(body: str) -> str:
    normalized = body.lower()
    if "serrur" in normalized or "lock" in normalized:
        return "locksmith"
    if "electric" in normalized:
        return "electrician"
    if (
        "plumb" in normalized
        or "plomb" in normalized
        or "leak" in normalized
        or "water" in normalized
        or "fuite" in normalized
        or "lavabo" in normalized
        or "siphon" in normalized
        or "evier" in normalized
    ):
        return "plumber"
    if "heat" in normalized or "boiler" in normalized or "chauffage" in normalized:
        return "heating"
    return "general maintenance"


def _should_force_landlord_contact(
    result: AgentTurnResult,
    current_turn: dict[str, Any],
) -> bool:
    if current_turn.get("sender_role") != "tenant":
        return False
    if _has_outgoing_role(result, "landlord"):
        return False
    if _asked_tenant_question(result):
        return False
    return _is_repair_request(current_turn.get("body", ""))


def _should_force_provider_contact(
    result: AgentTurnResult,
    property_context: dict[str, Any],
    current_turn: dict[str, Any],
) -> bool:
    if _is_landlord_supplied_provider_turn(current_turn):
        return False
    if not _is_landlord_provider_approval_turn(current_turn):
        return False
    if _has_successful_tool_call(result, "provider.contact"):
        return False
    return not _provider_contact_sent_in_context(property_context)


def _has_outgoing_role(result: AgentTurnResult, role: str) -> bool:
    return any(message.get("to_role") == role for message in result.outgoing_messages)


def _asked_tenant_question(result: AgentTurnResult) -> bool:
    return any(
        call.get("name") == "messaging.ask_question"
        and call.get("arguments", {}).get("to_role") == "tenant"
        for call in result.tool_calls
    )


def _has_successful_tool_call(result: AgentTurnResult, name: str) -> bool:
    return any(call.get("name") == name and call.get("output", {}).get("ok") is True for call in result.tool_calls)


def _provider_contact_sent_in_context(property_context: dict[str, Any]) -> bool:
    for action in property_context.get("recent_actions", []):
        if action.get("kind") != "provider.contact":
            continue
        payload = action.get("payload") or {}
        message_result = payload.get("message_result") or {}
        if message_result.get("sent") is True:
            return True
    return False


def _is_repair_request(body: str) -> bool:
    normalized = body.lower()
    repair_terms = [
        "boiler",
        "broken",
        "chauffage",
        "chaudiere",
        "degat",
        "electric",
        "eau",
        "evier",
        "fuite",
        "fuit",
        "heating",
        "lavabo",
        "leak",
        "lock",
        "locksmith",
        "panne",
        "parquet",
        "plomb",
        "plumb",
        "porte",
        "radiateur",
        "repair",
        "serrure",
        "sink",
        "siphon",
        "water",
    ]
    return any(term in normalized for term in repair_terms)


def _is_landlord_provider_approval_turn(current_turn: dict[str, Any]) -> bool:
    if current_turn.get("sender_role") != "landlord":
        return False
    body = str(current_turn.get("body", "")).lower().strip()
    approval_terms = [
        "approve",
        "approved",
        "autorise",
        "d'accord",
        "go",
        "ok",
        "oui",
        "yes",
        "vas-y",
        "valide",
    ]
    rejection_terms = ["non", "no", "refuse", "attends", "pas encore"]
    return any(term in body for term in approval_terms) and not any(term in body for term in rejection_terms)


def _is_landlord_supplied_provider_turn(current_turn: dict[str, Any]) -> bool:
    if current_turn.get("sender_role") != "landlord":
        return False
    body = str(current_turn.get("body", ""))
    return bool(_extract_landlord_phone(body) or _extract_landlord_email(body))


def _extract_landlord_phone(body: str) -> str | None:
    match = re.search(r"(?:\+33|0033|0)\s?[1-9](?:[\s.-]?\d{2}){4}", body)
    if not match:
        return None
    raw = match.group(0).strip()
    clean = raw.replace(" ", "").replace(".", "").replace("-", "")
    if clean.startswith("0033"):
        return f"+33{clean[4:]}"
    if clean.startswith("0") and len(clean) == 10:
        return f"+33{clean[1:]}"
    return clean


def _extract_landlord_email(body: str) -> str | None:
    match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", body)
    return match.group(0).lower() if match else None


def _extract_landlord_provider_name(body: str) -> str | None:
    phone_pattern = r"(?:\+33|0033|0)\s?[1-9](?:[\s.-]?\d{2}){4}"
    patterns = [
        rf"(?:contacte|appelle|message a|message à)\s+([A-ZÀ-Ÿ][A-Za-zÀ-ÿ' -]{{1,40}}?)\s+(?:au|a|à)\s+{phone_pattern}",
        r"(?:personne|prestataire)\s+(?:s'appelle|est)\s+([A-ZÀ-Ÿ][A-Za-zÀ-ÿ' -]{1,40})",
    ]
    for pattern in patterns:
        match = re.search(pattern, body, flags=re.IGNORECASE)
        if match:
            name = " ".join(match.group(1).split())
            if name:
                return name[:80]
    return None


def _mentions_quote_or_cost(body: str) -> bool:
    normalized = body.lower()
    return any(term in normalized for term in ["€", "eur", "devis", "quote", "cout", "prix", "price"])


def _preferred_provider_id(property_context: dict[str, Any], trade: str) -> str | None:
    preferred = property_context.get("preferred_providers", [])
    fallback = None
    for row in preferred:
        provider = row.get("provider") or {}
        if fallback is None:
            fallback = provider.get("id")
        if provider.get("trade", "").lower() == trade.lower():
            return provider.get("id")
    return fallback


def _matching_preferred_provider(property_context: dict[str, Any], trade: str) -> dict[str, Any] | None:
    for row in property_context.get("preferred_providers", []):
        provider = row.get("provider") or {}
        if provider.get("trade", "").lower() == trade.lower():
            return provider
    return None


def _first_search_provider_id(search_output: dict[str, Any]) -> str | None:
    for candidate in search_output.get("candidates", []):
        provider_id = candidate.get("provider_id")
        if provider_id:
            return provider_id
    return None


def _request_text(property_context: dict[str, Any], current_turn: dict[str, Any]) -> str:
    parts = [str(current_turn.get("body", ""))]
    for conversation in property_context.get("conversations", []):
        for message in conversation.get("messages", [])[-3:]:
            if message.get("role") in {"tenant", "landlord"}:
                parts.append(str(message.get("body", "")))
    return " ".join(parts)


def _provider_repair_brief(property_context: dict[str, Any], current_turn: dict[str, Any]) -> str:
    prop = property_context.get("property") or {}
    tenant = property_context.get("tenant") or {}
    address = prop.get("address") or "the property"
    access = prop.get("access_details") or {}
    request_text = _request_text(property_context, current_turn)
    return (
        f"Repair request for {address}. Tenant: {tenant.get('name', 'tenant')}. "
        f"Tenant/property context: {request_text}. Access details: {_json_dump(access)}. "
        "Please confirm your earliest availability, expected visit duration, and whether you need more details."
    )


def _landlord_repair_approval_question(
    property_context: dict[str, Any],
    current_turn: dict[str, Any],
    trade: str,
    preferred_provider: dict[str, Any] | None,
    search_output: dict[str, Any] | None,
) -> str:
    tenant_name = property_context.get("tenant", {}).get("name") or "Le locataire"
    landlord_name = property_context.get("landlord", {}).get("name") or ""
    address = property_context.get("property", {}).get("address") or "le logement"
    message = _one_line_no_question_mark(current_turn.get("body", ""))
    greeting = f"Bonjour {landlord_name}, " if landlord_name else "Bonjour, "
    provider_block = _landlord_provider_block(preferred_provider, search_output)
    return (
        f"{greeting}\n"
        f"Recap demande locataire:\n"
        f"- Locataire: {tenant_name}\n"
        f"- Adresse: {address}\n"
        f"- Type probable: {trade}\n"
        f"- Probleme et disponibilites: {message}\n\n"
        f"{provider_block}\n\n"
        "Vous pouvez valider une option, refuser ces options, ou me donner le numero/email "
        "de la personne que vous voulez que je contacte. Souhaitez-vous que je lance la coordination ?"
    )


def _landlord_provider_block(
    preferred_provider: dict[str, Any] | None,
    search_output: dict[str, Any] | None,
) -> str:
    if preferred_provider:
        return (
            "Prestataire prefere en base:\n"
            f"- {preferred_provider.get('name')} ({preferred_provider.get('trade')})"
        )

    candidates = (search_output or {}).get("candidates") or []
    if not candidates:
        return "Aucun prestataire prefere en base. Je n'ai pas encore de candidat externe fiable."

    lines = ["Aucun prestataire prefere en base. Options proches trouvees via Tavily:"]
    for index, candidate in enumerate(candidates[:3], start=1):
        title = _one_line_no_question_mark(candidate.get("title", "Prestataire"))
        url = _display_url(candidate.get("url"))
        lines.append(f"{index}. {title} - {url}")
    return "\n".join(lines)


def _one_line_no_question_mark(value: Any) -> str:
    return " ".join(str(value or "").replace("?", ".").split())


def _display_url(value: str | None) -> str:
    if not value:
        return "contact web"
    return value.split("?", 1)[0]


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
        "7. If the landlord supplies a specific phone or email, call `provider__register_contact` "
        "before `provider__contact`.\n"
        "8. After landlord approval, call `provider__contact` to bring the repair provider into the workflow.\n"
        "9. When a provider replies, coordinate the triangle: tenant confirms access/slots, "
        "landlord approves costs or scope changes, provider receives only scoped operational details.\n"
        "10. Ask one concise question only when required information is genuinely missing.\n\n"
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
