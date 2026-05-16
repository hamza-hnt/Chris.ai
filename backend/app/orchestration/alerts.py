from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal


AlertSeverity = Literal["low", "medium", "high", "critical"]


@dataclass(frozen=True)
class Alert:
    kind: str
    severity: AlertSeverity
    message: str
    payload: dict[str, Any]


AlertRule = Callable[[dict[str, Any]], Alert | None]


def landlord_no_response(state: dict[str, Any]) -> Alert | None:
    if state.get("landlord_waiting_days", 0) >= 2:
        return Alert("landlord-no-response", "medium", "Landlord response is overdue.", state)
    return None


def workflow_no_progress(state: dict[str, Any]) -> Alert | None:
    if state.get("workflow_idle_days", 0) >= 3:
        return Alert("workflow-no-progress", "medium", "Workflow has not progressed.", state)
    return None


def rent_overdue(state: dict[str, Any]) -> Alert | None:
    if state.get("rent_overdue") is True:
        return Alert("rent-overdue", "high", "Rent is overdue.", state)
    return None


def quote_pending(state: dict[str, Any]) -> Alert | None:
    if state.get("quote_pending_days", 0) >= 2:
        return Alert("quote-pending", "medium", "Provider quote is still pending.", state)
    return None


def provider_job_pending(state: dict[str, Any]) -> Alert | None:
    if state.get("provider_job_pending_days", 0) >= 2:
        return Alert("provider-job-pending", "medium", "Provider job needs follow-up.", state)
    return None


def agent_stuck_flag(state: dict[str, Any]) -> Alert | None:
    if state.get("agent_stuck") is True:
        return Alert("agent-stuck-flag", "high", "Agent flagged that it is stuck.", state)
    return None


def tenant_distress_flag(state: dict[str, Any]) -> Alert | None:
    if state.get("tenant_distress") is True:
        return Alert("tenant-distress-flag", "high", "Tenant message indicates distress.", state)
    return None


def maintenance_date_approaching(state: dict[str, Any]) -> Alert | None:
    if state.get("maintenance_due_days", 99) <= 2:
        return Alert(
            "maintenance-date-approaching",
            "low",
            "Maintenance date is approaching.",
            state,
        )
    return None


def legal_document_produced(state: dict[str, Any]) -> Alert | None:
    if state.get("legal_document_produced") is True:
        return Alert(
            "legal-document-produced",
            "low",
            "A legal document was produced and should be visible to supervisors.",
            state,
        )
    return None


RULES: list[AlertRule] = [
    landlord_no_response,
    workflow_no_progress,
    rent_overdue,
    quote_pending,
    provider_job_pending,
    agent_stuck_flag,
    tenant_distress_flag,
    maintenance_date_approaching,
    legal_document_produced,
]


def evaluate_alerts(state: dict[str, Any]) -> list[Alert]:
    return [alert for rule in RULES if (alert := rule(state)) is not None]
