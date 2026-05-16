from uuid import UUID

from app.agent.tools.executor import ToolExecutionContext
from app.domain.repositories import plans
from app.domain.repositories.serialization import model_to_dict


def review_or_create(context: ToolExecutionContext, arguments: dict) -> dict:
    plan = plans.review_or_create_plan(
        context.property_id,
        context.db,
        arguments["plan_name"],
        arguments.get("steps", []),
    )
    return {
        "ok": True,
        "plan": model_to_dict(
            plan, ["id", "property_id", "name", "status", "steps", "created_at", "updated_at"]
        ),
    }


def mark_step(context: ToolExecutionContext, arguments: dict) -> dict:
    plan = plans.mark_step(
        context.property_id,
        context.db,
        UUID(arguments["plan_id"]),
        int(arguments["step_index"]),
        arguments["status"],
        arguments.get("evidence"),
    )
    return {
        "ok": True,
        "plan": model_to_dict(
            plan, ["id", "property_id", "name", "status", "steps", "created_at", "updated_at"]
        ),
    }


def revise(context: ToolExecutionContext, arguments: dict) -> dict:
    plan = plans.revise_plan(
        context.property_id,
        context.db,
        UUID(arguments["plan_id"]),
        arguments["new_steps"],
    )
    return {
        "ok": True,
        "plan": model_to_dict(
            plan, ["id", "property_id", "name", "status", "steps", "created_at", "updated_at"]
        ),
    }
