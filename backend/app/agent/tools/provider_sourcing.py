from uuid import UUID

from app.agent.tools.executor import ToolExecutionContext
from app.domain.repositories.memory import append_action
from app.domain.repositories.providers import get_provider, list_preferred_providers
from app.domain.repositories.serialization import model_to_dict
from app.integrations.tavily import tavily_search


def list_preferred(context: ToolExecutionContext, arguments: dict) -> dict:
    providers = list_preferred_providers(context.property_id, context.db, arguments.get("trade"))
    return {"ok": True, "providers": providers}


def search(context: ToolExecutionContext, arguments: dict) -> dict:
    trade = arguments["trade"]
    area = arguments["area"]
    constraints = arguments.get("constraints") or ""
    query = f"{trade} contractor near {area}. {constraints}".strip()
    result = tavily_search(query)
    append_action(context.property_id, context.db, "provider.search", {"query": query})
    return {"ok": True, "search": result}


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
