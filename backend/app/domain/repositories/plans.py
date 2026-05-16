from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Plan, PlanStatus
from app.orchestration.isolation import scoped


def review_or_create_plan(property_id: UUID, db: Session, plan_name: str, steps: list[dict]) -> Plan:
    with scoped(property_id) as pid:
        plan = db.execute(
            select(Plan).where(
                Plan.property_id == pid,
                Plan.name == plan_name,
                Plan.status == PlanStatus.active,
            )
        ).scalar_one_or_none()
        if plan is None:
            plan = Plan(property_id=pid, name=plan_name, steps=steps, status=PlanStatus.active)
            db.add(plan)
        else:
            plan.updated_at = datetime.now(UTC)
        db.flush()
        return plan


def mark_step(
    property_id: UUID,
    db: Session,
    plan_id: UUID,
    step_index: int,
    status: str,
    evidence: str | None = None,
) -> Plan:
    with scoped(property_id) as pid:
        plan = db.execute(select(Plan).where(Plan.property_id == pid, Plan.id == plan_id)).scalar_one()
        steps = [dict(step) for step in plan.steps]
        steps[step_index]["status"] = status
        if evidence:
            steps[step_index]["evidence"] = evidence
        plan.steps = steps
        plan.updated_at = datetime.now(UTC)
        db.flush()
        return plan


def revise_plan(property_id: UUID, db: Session, plan_id: UUID, new_steps: list[dict]) -> Plan:
    with scoped(property_id) as pid:
        plan = db.execute(select(Plan).where(Plan.property_id == pid, Plan.id == plan_id)).scalar_one()
        plan.steps = new_steps
        plan.updated_at = datetime.now(UTC)
        db.flush()
        return plan
