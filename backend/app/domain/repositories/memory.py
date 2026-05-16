from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import ActionLog, Conversation, ConversationParty, ToolTrace
from app.orchestration.isolation import scoped


def append_action(property_id: UUID, db: Session, kind: str, payload: dict) -> ActionLog:
    with scoped(property_id) as pid:
        action = ActionLog(property_id=pid, kind=kind, payload=payload)
        db.add(action)
        db.flush()
        return action


def append_message(
    property_id: UUID,
    db: Session,
    party: ConversationParty,
    thread_id: str,
    message: dict,
) -> Conversation:
    with scoped(property_id) as pid:
        conversation = db.execute(
            select(Conversation).where(
                Conversation.property_id == pid,
                Conversation.party == party,
                Conversation.thread_id == thread_id,
            )
        ).scalar_one_or_none()
        if conversation is None:
            conversation = Conversation(
                property_id=pid,
                party=party,
                thread_id=thread_id,
                messages=[],
            )
            db.add(conversation)
            db.flush()

        conversation.messages = [
            *conversation.messages,
            {**message, "ts": message.get("ts") or datetime.now(UTC).isoformat()},
        ]
        conversation.updated_at = datetime.now(UTC)
        db.flush()
        return conversation


def record_tool_trace(
    property_id: UUID,
    db: Session,
    turn_id: str,
    tool_name: str,
    tool_input: dict,
    output: dict,
    duration_ms: int,
) -> ToolTrace:
    with scoped(property_id) as pid:
        trace = ToolTrace(
            property_id=pid,
            turn_id=turn_id,
            tool_name=tool_name,
            input=tool_input,
            output=output,
            duration_ms=duration_ms,
        )
        db.add(trace)
        db.flush()
        return trace
