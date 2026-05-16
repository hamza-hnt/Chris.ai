from typing import Any


def object_schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "plan.review_or_create",
        "description": "Review the current plan for this request, creating it if missing.",
        "parameters": object_schema(
            {
                "plan_name": {"type": "string"},
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["pending", "in_progress", "blocked", "done"],
                            },
                            "evidence": {"type": ["string", "null"]},
                        },
                        "required": ["description", "status"],
                        "additionalProperties": False,
                    },
                },
            },
            ["plan_name", "steps"],
        ),
    },
    {
        "name": "plan.mark_step",
        "description": "Update progress for a plan step with optional evidence.",
        "parameters": object_schema(
            {
                "plan_id": {"type": "string"},
                "step_index": {"type": "integer", "minimum": 0},
                "status": {"type": "string", "enum": ["pending", "in_progress", "blocked", "done"]},
                "evidence": {"type": ["string", "null"]},
            },
            ["plan_id", "step_index", "status"],
        ),
    },
    {
        "name": "plan.revise",
        "description": "Replace plan steps when the scope changes.",
        "parameters": object_schema(
            {
                "plan_id": {"type": "string"},
                "new_steps": {"type": "array", "items": {"type": "object"}},
            },
            ["plan_id", "new_steps"],
        ),
    },
    {
        "name": "messaging.send",
        "description": "Send a message to a tenant, landlord, or provider through a stubbed channel.",
        "parameters": object_schema(
            {
                "to_role": {"type": "string", "enum": ["tenant", "landlord", "provider"]},
                "channel": {"type": "string", "enum": ["whatsapp", "email", "voice"]},
                "body": {"type": "string"},
                "attachments": {"type": "array", "items": {"type": "string"}},
            },
            ["to_role", "channel", "body"],
        ),
    },
    {
        "name": "messaging.ask_question",
        "description": "Ask exactly one question to a tenant, landlord, or provider.",
        "parameters": object_schema(
            {
                "to_role": {"type": "string", "enum": ["tenant", "landlord", "provider"]},
                "body": {"type": "string"},
            },
            ["to_role", "body"],
        ),
    },
    {
        "name": "provider.list_preferred",
        "description": "List landlord-preferred contractors for this property and trade.",
        "parameters": object_schema({"trade": {"type": "string"}}, ["trade"]),
    },
    {
        "name": "provider.search",
        "description": "Search for outside providers using Tavily.",
        "parameters": object_schema(
            {
                "trade": {"type": "string"},
                "area": {"type": "string"},
                "constraints": {"type": "string"},
            },
            ["trade", "area"],
        ),
    },
    {
        "name": "provider.contact",
        "description": "Open a provider thread with a scoped work brief.",
        "parameters": object_schema(
            {"provider_id": {"type": "string"}, "brief": {"type": "string"}},
            ["provider_id", "brief"],
        ),
    },
    {
        "name": "documents.create_receipt",
        "description": "Create a rent receipt only for a landlord-confirmed payment row.",
        "parameters": object_schema({"payment_id": {"type": "string"}}, ["payment_id"]),
    },
    {
        "name": "documents.create_intervention_report",
        "description": "Create an intervention report from authoritative job data.",
        "parameters": object_schema({"job_id": {"type": "string"}}, ["job_id"]),
    },
    {
        "name": "documents.create_quote_summary",
        "description": "Create a quote summary for landlord review from received quotes.",
        "parameters": object_schema({"job_id": {"type": "string"}}, ["job_id"]),
    },
    {
        "name": "web_search",
        "description": "Run a Tavily web search for real-time external information.",
        "parameters": object_schema({"query": {"type": "string"}}, ["query"]),
    },
    {
        "name": "escalate",
        "description": "Flag the turn for supervisor attention.",
        "parameters": object_schema(
            {
                "reason": {"type": "string"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
            },
            ["reason", "severity"],
        ),
    },
]
