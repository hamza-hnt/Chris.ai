from typing import Literal

from sqlalchemy.orm import Session

from app.agent.chris import ChrisAgent
from app.db import SessionLocal
from app.domain.repositories.context import load_property_context
from app.domain.repositories.serialization import to_jsonable
from app.orchestration.router import resolve_sender


def run_incoming_message(
    db: Session,
    sender_contact: str,
    body: str,
    channel: Literal["whatsapp", "email", "voice", "supervisor"] = "whatsapp",
    thread_id: str = "sample",
) -> dict:
    route = resolve_sender(db, sender_contact)
    if route is None:
        return {"status": "dropped", "reason": "unknown_contact"}

    property_context = load_property_context(route.property_id, db)
    current_turn = {
        "sender_contact": sender_contact,
        "sender_role": route.sender_role,
        "channel": channel,
        "body": body,
        "thread_id": thread_id,
    }
    result = ChrisAgent().run_turn(db, property_context, current_turn)
    db.commit()
    return {
        "status": "ok",
        "property_id": str(route.property_id),
        "sender_role": route.sender_role,
        "turn_id": result.turn_id,
        "tool_calls": to_jsonable(result.tool_calls),
        "outgoing_messages": to_jsonable(result.outgoing_messages),
    }


def main() -> None:
    with SessionLocal() as db:
        result = run_incoming_message(
            db,
            sender_contact="+33600000001",
            body="There is a leak under the kitchen sink. Can I choose a plumber?",
            channel="whatsapp",
            thread_id="sample-cli",
        )
        print(to_jsonable(result))


if __name__ == "__main__":
    main()
