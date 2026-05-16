from app.agent.tools.executor import ToolExecutionContext
from app.domain.models import ConversationParty
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
        result = send_whatsapp(to_role, body, attachments)
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
