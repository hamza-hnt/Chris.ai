from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.domain.models import (
    ActionLog,
    AgentContext,
    Conversation,
    Lease,
    Plan,
    PlanStatus,
    Property,
    PropertyPreferredProvider,
)
from app.domain.repositories.serialization import model_to_dict, to_jsonable
from app.orchestration.isolation import scoped


def load_property_context(property_id: UUID, db: Session) -> dict:
    with scoped(property_id) as pid:
        prop = db.get(Property, pid)
        if prop is None:
            raise LookupError(f"Property not found: {pid}")

        lease = db.execute(select(Lease).where(Lease.property_id == pid)).scalar_one_or_none()
        agent_context = db.get(AgentContext, pid)

        preferred_rows = db.execute(
            select(PropertyPreferredProvider)
            .where(PropertyPreferredProvider.property_id == pid)
            .order_by(PropertyPreferredProvider.rank.asc())
        ).scalars()

        conversations = db.execute(
            select(Conversation)
            .where(Conversation.property_id == pid)
            .order_by(desc(Conversation.updated_at))
            .limit(5)
        ).scalars()

        plans = db.execute(
            select(Plan)
            .where(Plan.property_id == pid, Plan.status == PlanStatus.active)
            .order_by(desc(Plan.updated_at))
        ).scalars()

        actions = db.execute(
            select(ActionLog)
            .where(ActionLog.property_id == pid)
            .order_by(desc(ActionLog.created_at))
            .limit(10)
        ).scalars()

        tenant = lease.tenant if lease else None
        landlord = lease.landlord if lease else None

        return {
            "property_id": str(pid),
            "property": model_to_dict(
                prop,
                ["id", "org_id", "address", "type", "size", "equipment", "access_details", "status"],
            ),
            "lease": model_to_dict(
                lease,
                [
                    "id",
                    "property_id",
                    "tenant_id",
                    "landlord_id",
                    "rent",
                    "charges",
                    "payment_due_day",
                    "deposit",
                    "start_date",
                    "end_date",
                    "lease_type",
                ],
            )
            if lease
            else None,
            "tenant": model_to_dict(tenant, ["id", "name", "email", "phone", "role"])
            if tenant
            else None,
            "landlord": model_to_dict(landlord, ["id", "name", "email", "phone", "role"])
            if landlord
            else None,
            "preferred_providers": [
                {
                    "rank": row.rank,
                    "provider": model_to_dict(row.provider, ["id", "name", "trade", "contacts"]),
                }
                for row in preferred_rows
            ],
            "agent_context": {
                "summary": agent_context.summary if agent_context else "",
                "sensitive_notes": agent_context.sensitive_notes if agent_context else {},
            },
            "conversations": [
                model_to_dict(row, ["id", "party", "thread_id", "messages", "updated_at"])
                for row in conversations
            ],
            "active_plans": [
                model_to_dict(row, ["id", "name", "status", "steps", "created_at", "updated_at"])
                for row in plans
            ],
            "recent_actions": [
                model_to_dict(row, ["id", "kind", "payload", "created_at"]) for row in actions
            ],
        }


def assert_single_property_context(context: dict) -> None:
    property_id = str(context.get("property_id", ""))
    if not property_id:
        raise ValueError("Prompt context must include property_id.")

    serialized = to_jsonable(context)
    seen: set[str] = set()

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "property_id":
                    seen.add(str(child))
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(serialized)
    mixed = {pid for pid in seen if pid != property_id}
    if mixed:
        raise ValueError(
            f"Prompt context mixes property scopes. expected={property_id} mixed={sorted(mixed)}"
        )
