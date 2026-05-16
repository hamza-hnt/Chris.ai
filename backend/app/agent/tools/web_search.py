from app.agent.tools.executor import ToolExecutionContext
from app.domain.repositories.memory import append_action
from app.integrations.tavily import tavily_search


def search(context: ToolExecutionContext, arguments: dict) -> dict:
    query = arguments["query"].strip()
    result = tavily_search(query)
    append_action(context.property_id, context.db, "web_search", {"query": query})
    return {"ok": True, "result": result}
