from uuid import UUID

from sqlalchemy import select

from app.agent.tools.executor import ToolExecutionContext
from app.domain.models import Property
from app.domain.repositories.memory import append_action
from app.domain.repositories.providers import get_provider, list_preferred_providers
from app.domain.repositories.serialization import model_to_dict, to_jsonable
from app.integrations.tavily import tavily_search


def list_preferred(context: ToolExecutionContext, arguments: dict) -> dict:
    providers = list_preferred_providers(context.property_id, context.db, arguments.get("trade"))
    return {"ok": True, "providers": providers}


def search(context: ToolExecutionContext, arguments: dict) -> dict:
    trade = arguments["trade"].strip()
    property_address = _property_address(context)
    area = (arguments.get("area") or property_address).strip()
    constraints = (arguments.get("constraints") or "").strip()
    query = _provider_query(trade, area, property_address, constraints)
    result = tavily_search(query)
    candidates = _normalize_tavily_results(result)
    append_action(
        context.property_id,
        context.db,
        "provider.search",
        {
            "trade": trade,
            "area": area,
            "property_address": property_address,
            "constraints": constraints,
            "query": query,
            "candidate_count": len(candidates),
        },
    )
    return {
        "ok": True,
        "trade": trade,
        "area": area,
        "property_address": property_address,
        "query": query,
        "candidates": candidates,
        "raw_search": to_jsonable(result),
    }


def contact(context: ToolExecutionContext, arguments: dict) -> dict:
    provider = get_provider(context.property_id, context.db, UUID(arguments["provider_id"]))
    brief = arguments["brief"].strip()
    append_action(
        context.property_id,
        context.db,
        "provider.contact",
        {"provider_id": str(provider.id), "brief": brief},
    )
    return {
        "ok": True,
        "provider": model_to_dict(provider, ["id", "name", "trade", "contacts"]),
        "thread_opened": True,
    }


def _property_address(context: ToolExecutionContext) -> str:
    prop = context.db.execute(
        select(Property).where(Property.id == context.property_id)
    ).scalar_one_or_none()
    return prop.address if prop else ""


def _provider_query(trade: str, area: str, property_address: str, constraints: str) -> str:
    parts = [
        f"{trade} repair service near {area}",
        "local contractor",
        "phone email emergency availability",
    ]
    if property_address and property_address != area:
        parts.append(f"property address {property_address}")
    if constraints:
        parts.append(constraints)
    return ". ".join(parts)


def _normalize_tavily_results(result: dict) -> list[dict]:
    candidates = []
    for item in result.get("results", [])[:5]:
        candidates.append(
            {
                "title": item.get("title") or item.get("name") or "Unknown provider",
                "url": item.get("url"),
                "content": item.get("content") or item.get("snippet") or "",
                "score": item.get("score"),
            }
        )
    return candidates
