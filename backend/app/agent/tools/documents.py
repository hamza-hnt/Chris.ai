from uuid import UUID

from app.agent.tools.executor import ToolExecutionContext
from app.domain.models import DocumentKind
from app.domain.repositories.documents import create_receipt, create_stub_document
from app.domain.repositories.memory import append_action
from app.domain.repositories.serialization import model_to_dict


def receipt(context: ToolExecutionContext, arguments: dict) -> dict:
    document = create_receipt(
        context.property_id,
        context.db,
        UUID(arguments["payment_id"]),
        triggered_by=context.sender_role,
    )
    append_action(
        context.property_id,
        context.db,
        "documents.create_receipt",
        {"payment_id": arguments["payment_id"], "document_id": str(document.id)},
    )
    return {"ok": True, "document": model_to_dict(document, ["id", "kind", "payload", "created_at"])}


def intervention_report(context: ToolExecutionContext, arguments: dict) -> dict:
    document = create_stub_document(
        context.property_id,
        context.db,
        DocumentKind.intervention_report,
        {"job_id": arguments["job_id"], "status": "stubbed"},
        triggered_by=context.sender_role,
    )
    append_action(
        context.property_id,
        context.db,
        "documents.create_intervention_report",
        {"job_id": arguments["job_id"], "document_id": str(document.id)},
    )
    return {"ok": True, "document": model_to_dict(document, ["id", "kind", "payload", "created_at"])}


def quote_summary(context: ToolExecutionContext, arguments: dict) -> dict:
    document = create_stub_document(
        context.property_id,
        context.db,
        DocumentKind.quote,
        {"job_id": arguments["job_id"], "status": "stubbed"},
        triggered_by=context.sender_role,
    )
    append_action(
        context.property_id,
        context.db,
        "documents.create_quote_summary",
        {"job_id": arguments["job_id"], "document_id": str(document.id)},
    )
    return {"ok": True, "document": model_to_dict(document, ["id", "kind", "payload", "created_at"])}
