from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.repositories.memory import append_action


InterventionKind = Literal["direct_instruction", "takeover", "force_escalation"]


@dataclass(frozen=True)
class InterventionResult:
    property_id: UUID
    kind: InterventionKind
    status: str
    recorded_at: str


def direct_instruction(db: Session, property_id: UUID, instruction: str) -> InterventionResult:
    result = InterventionResult(property_id, "direct_instruction", "recorded", _now())
    append_action(property_id, db, "supervisor.direct_instruction", {"instruction": instruction})
    return result


def takeover(db: Session, property_id: UUID, reason: str) -> InterventionResult:
    result = InterventionResult(property_id, "takeover", "agent_paused", _now())
    append_action(property_id, db, "supervisor.takeover", {"reason": reason})
    return result


def force_escalation(db: Session, property_id: UUID, reason: str) -> InterventionResult:
    result = InterventionResult(property_id, "force_escalation", "escalated", _now())
    append_action(property_id, db, "supervisor.force_escalation", {"reason": reason})
    return result


def _now() -> str:
    return datetime.now(UTC).isoformat()


def to_dict(result: InterventionResult) -> dict:
    data = asdict(result)
    data["property_id"] = str(result.property_id)
    return data
