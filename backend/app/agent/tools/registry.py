from app.agent.tools import documents, escalation, messaging, plan, provider_sourcing, web_search
from app.agent.tools.executor import ToolExecutor


def build_tool_executor() -> ToolExecutor:
    return ToolExecutor(
        {
            "plan.review_or_create": plan.review_or_create,
            "plan.mark_step": plan.mark_step,
            "plan.revise": plan.revise,
            "messaging.send": messaging.send,
            "messaging.ask_question": messaging.ask_question,
            "provider.list_preferred": provider_sourcing.list_preferred,
            "provider.search": provider_sourcing.search,
            "provider.register_contact": provider_sourcing.register_contact,
            "provider.contact": provider_sourcing.contact,
            "documents.create_receipt": documents.receipt,
            "documents.create_intervention_report": documents.intervention_report,
            "documents.create_quote_summary": documents.quote_summary,
            "web_search": web_search.search,
            "escalate": escalation.escalate,
        }
    )
