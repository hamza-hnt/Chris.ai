from uuid import UUID

from sqlalchemy import desc, select

from app.agent.tools.executor import ToolExecutionContext
from app.domain.models import ActionLog, ConversationParty, Lease, Provider
from app.domain.repositories.memory import append_action, append_message
from app.integrations.email_stub import send_email
from app.integrations.slng_stub import send_voice
from app.integrations.whatsapp_stub import send_whatsapp


def send(context: ToolExecutionContext, arguments: dict) -> dict:
    channel = arguments["channel"]
    to_role = arguments["to_role"]
    body = arguments["body"].strip()
    attachments = arguments.get("attachments") or []
    if channel == "whatsapp":
        result = send_whatsapp(
            to_role,
            body,
            attachments,
            to_phone=_resolve_role_phone(context, to_role),
        )
    elif channel == "email":
        result = send_email(to_role, body, attachments)
    elif channel == "voice":
        result = send_voice(to_role, body, attachments)
    else:
        raise ValueError(f"Unsupported channel: {channel}")

    append_action(
        context.property_id,
        context.db,
        "messaging.send",
        {"to_role": to_role, "channel": channel, "body": body, "attachments": attachments},
    )
    if to_role in {"tenant", "landlord", "provider"}:
        append_message(
            context.property_id,
            context.db,
            ConversationParty(to_role),
            f"{channel}-{to_role}",
            {"role": "agent", "body": body, "channel": channel},
        )
    return {"ok": True, "message": result}


def _resolve_role_phone(context: ToolExecutionContext, to_role: str) -> str | None:
    lease = (
        context.db.execute(
            select(Lease)
            .where(Lease.property_id == context.property_id)
            .order_by(Lease.start_date.desc())
        )
        .scalars()
        .first()
    )
    if lease is None:
        return None
    if to_role == "tenant":
        return lease.tenant.phone
    if to_role == "landlord":
        return lease.landlord.phone
    if to_role == "provider":
        return _latest_provider_phone(context)
    return None


def _latest_provider_phone(context: ToolExecutionContext) -> str | None:
    action = (
        context.db.execute(
            select(ActionLog)
            .where(ActionLog.property_id == context.property_id, ActionLog.kind == "provider.contact")
            .order_by(desc(ActionLog.created_at))
        )
        .scalars()
        .first()
    )
    if action is None:
        return None
    provider_id = (action.payload or {}).get("provider_id")
    if not provider_id:
        return None
    provider = context.db.get(Provider, UUID(str(provider_id)))
    if provider is None:
        return None
    return (provider.contacts or {}).get("phone")


def ask_question(context: ToolExecutionContext, arguments: dict) -> dict:
    body = arguments["body"].strip()
    question_count = body.count("?")
    if question_count != 1:
        raise ValueError("messaging.ask_question requires exactly one question.")
    return send(
        context,
        {
            "to_role": arguments["to_role"],
            "channel": "whatsapp",
            "body": body,
            "attachments": [],
        },
    )
