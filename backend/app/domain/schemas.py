from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class MessageRecord(BaseModel):
    role: Literal["tenant", "landlord", "provider", "supervisor", "agent", "tool"]
    body: str
    ts: str
    channel: Literal["whatsapp", "email", "voice", "supervisor", "system"]


class PlanStep(BaseModel):
    description: str
    status: Literal["pending", "in_progress", "blocked", "done"] = "pending"
    evidence: str | None = None


class PropertyContext(BaseModel):
    property_id: UUID
    property: dict[str, Any]
    lease: dict[str, Any] | None = None
    tenant: dict[str, Any] | None = None
    landlord: dict[str, Any] | None = None
    preferred_providers: list[dict[str, Any]] = Field(default_factory=list)
    agent_context: dict[str, Any] = Field(default_factory=dict)
    conversations: list[dict[str, Any]] = Field(default_factory=list)
    active_plans: list[dict[str, Any]] = Field(default_factory=list)
    recent_actions: list[dict[str, Any]] = Field(default_factory=list)


class IncomingMessage(BaseModel):
    sender_contact: str
    sender_role: Literal["tenant", "landlord", "provider", "supervisor"]
    channel: Literal["whatsapp", "email", "voice", "supervisor"]
    body: str
    thread_id: str = "default"
