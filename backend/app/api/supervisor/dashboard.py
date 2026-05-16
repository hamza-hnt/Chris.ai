from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.domain.models import (
    ActionLog,
    Conversation,
    Lease,
    Plan,
    PlanStatus,
    Property,
    ToolTrace,
    User,
    UserRole,
)
from app.domain.repositories.serialization import model_to_dict, to_jsonable

router = APIRouter(tags=["supervisor-dashboard"])


@router.get("/dashboard")
def landlord_dashboard(
    landlord_id: UUID | None = None,
    landlord_phone: Annotated[str | None, Query()] = None,
    db: Session = Depends(get_db),
) -> dict:
    landlord = _resolve_landlord(db, landlord_id, landlord_phone)
    if landlord is None:
        raise HTTPException(status_code=404, detail="No landlord found for dashboard.")
    return build_landlord_dashboard(db, landlord)


def build_landlord_dashboard(db: Session, landlord: User) -> dict:
    leases = (
        db.execute(
            select(Lease)
            .where(Lease.landlord_id == landlord.id)
            .order_by(Lease.start_date.desc())
        )
        .scalars()
        .all()
    )

    properties = [_property_row(db, lease) for lease in leases]
    requests = [request for row in properties for request in row["requests"]]
    return _dashboard_response(
        viewer=landlord,
        role="landlord",
        properties=properties,
        requests=requests,
    )


def build_tenant_dashboard(db: Session, tenant: User) -> dict:
    leases = (
        db.execute(
            select(Lease)
            .where(Lease.tenant_id == tenant.id)
            .order_by(Lease.start_date.desc())
        )
        .scalars()
        .all()
    )
    properties = [_property_row(db, lease) for lease in leases]
    requests = [request for row in properties for request in row["requests"]]
    return _dashboard_response(
        viewer=tenant,
        role="tenant",
        properties=properties,
        requests=requests,
    )


def _dashboard_response(
    viewer: User,
    role: str,
    properties: list[dict],
    requests: list[dict],
) -> dict:
    open_requests = [request for request in requests if request["status"] in {"active", "blocked"}]
    blocked_requests = [request for request in requests if request["status"] == "blocked"]
    pending_owner_decisions = sum(
        1 for request in requests if request.get("owner_action_required") is True
    )
    monthly_revenue = sum(float(row["lease"]["monthly_total"]) for row in properties)
    progress_values = [request["progress"] for request in open_requests]

    return {
        "viewer": model_to_dict(viewer, ["id", "name", "email", "phone", "role"]),
        "landlord": model_to_dict(viewer, ["id", "name", "email", "phone"])
        if viewer.role == UserRole.landlord
        else None,
        "role": role,
        "metrics": {
            "properties": len(properties),
            "tenants": len({row["tenant"]["id"] for row in properties if row.get("tenant")}),
            "open_requests": len(open_requests),
            "blocked_requests": len(blocked_requests),
            "pending_owner_decisions": pending_owner_decisions,
            "monthly_revenue": round(monthly_revenue, 2),
            "average_progress": round(sum(progress_values) / len(progress_values))
            if progress_values
            else 0,
        },
        "properties": properties,
        "requests": sorted(
            requests,
            key=lambda request: request["updated_at"] or request["created_at"] or "",
            reverse=True,
        ),
        "generated_from": "postgres",
    }


def _resolve_landlord(
    db: Session,
    landlord_id: UUID | None,
    landlord_phone: str | None,
) -> User | None:
    statement = select(User).where(User.role == UserRole.landlord)
    if landlord_id:
        statement = statement.where(User.id == landlord_id)
    elif landlord_phone:
        statement = statement.where(or_(User.phone == landlord_phone, User.email == landlord_phone))
    return db.execute(statement.order_by(User.created_at.asc())).scalar_one_or_none()


def _property_row(db: Session, lease: Lease) -> dict:
    prop = db.get(Property, lease.property_id)
    plans = (
        db.execute(
            select(Plan)
            .where(Plan.property_id == lease.property_id)
            .order_by(desc(Plan.updated_at))
        )
        .scalars()
        .all()
    )
    recent_actions = (
        db.execute(
            select(ActionLog)
            .where(ActionLog.property_id == lease.property_id)
            .order_by(desc(ActionLog.created_at))
            .limit(6)
        )
        .scalars()
        .all()
    )
    recent_traces = (
        db.execute(
            select(ToolTrace)
            .where(ToolTrace.property_id == lease.property_id)
            .order_by(desc(ToolTrace.created_at))
            .limit(8)
        )
        .scalars()
        .all()
    )
    conversations = (
        db.execute(
            select(Conversation)
            .where(Conversation.property_id == lease.property_id)
            .order_by(desc(Conversation.updated_at))
            .limit(4)
        )
        .scalars()
        .all()
    )
    total_traces = db.execute(
        select(func.count(ToolTrace.id)).where(ToolTrace.property_id == lease.property_id)
    ).scalar_one()

    return {
        "property": model_to_dict(
            prop,
            ["id", "address", "type", "size", "status", "equipment", "access_details"],
        ),
        "tenant": model_to_dict(lease.tenant, ["id", "name", "email", "phone"]),
        "lease": {
            **model_to_dict(
                lease,
                [
                    "id",
                    "rent",
                    "charges",
                    "payment_due_day",
                    "deposit",
                    "start_date",
                    "end_date",
                    "lease_type",
                ],
            ),
            "monthly_total": str(lease.rent + lease.charges),
        },
        "requests": [_request_row(plan, lease, prop) for plan in plans],
        "recent_actions": [
            model_to_dict(action, ["id", "kind", "payload", "created_at"]) for action in recent_actions
        ],
        "recent_tool_traces": [
            model_to_dict(trace, ["id", "turn_id", "tool_name", "input", "output", "created_at"])
            for trace in recent_traces
        ],
        "recent_conversations": [_conversation_preview(conversation) for conversation in conversations],
        "trace_count": total_traces,
    }


def _request_row(plan: Plan, lease: Lease, prop: Property) -> dict:
    steps = [dict(step) for step in plan.steps]
    done = sum(1 for step in steps if step.get("status") == "done")
    blocked = any(step.get("status") == "blocked" for step in steps)
    progress = round((done / len(steps)) * 100) if steps else 0
    status = "blocked" if blocked else plan.status.value
    next_step = next(
        (step.get("description", "Next action pending") for step in steps if step.get("status") != "done"),
        "Ready to close",
    )
    name_requires_owner = any(
        phrase in plan.name.lower()
        for phrase in ["choose", "pick", "provider", "contractor", "plumber", "electrician"]
    )
    owner_action = any(
        "landlord" in str(step.get("description", "")).lower()
        or "owner" in str(step.get("description", "")).lower()
        for step in steps
        if step.get("status") != "done"
    )

    return {
        "id": str(plan.id),
        "property_id": str(plan.property_id),
        "property_address": prop.address,
        "tenant_name": lease.tenant.name,
        "name": plan.name,
        "status": status,
        "progress": progress,
        "next_step": next_step,
        "owner_action_required": name_requires_owner or owner_action or plan.status == PlanStatus.blocked,
        "steps": to_jsonable(steps),
        "created_at": to_jsonable(plan.created_at),
        "updated_at": to_jsonable(plan.updated_at),
    }


def _conversation_preview(conversation: Conversation) -> dict:
    last_message = conversation.messages[-1] if conversation.messages else None
    return {
        "id": str(conversation.id),
        "party": conversation.party.value,
        "thread_id": conversation.thread_id,
        "updated_at": to_jsonable(conversation.updated_at),
        "last_message": last_message,
        "message_count": len(conversation.messages),
    }
