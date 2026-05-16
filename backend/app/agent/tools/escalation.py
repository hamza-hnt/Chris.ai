from app.agent.tools.executor import ToolExecutionContext
from app.domain.repositories.memory import append_action


def escalate(context: ToolExecutionContext, arguments: dict) -> dict:
    payload = {
        "reason": arguments["reason"].strip(),
        "severity": arguments["severity"],
        "sender_role": context.sender_role,
    }
    append_action(context.property_id, context.db, "escalate", payload)
    return {"ok": True, "escalation": payload}
