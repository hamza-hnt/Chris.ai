from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.orchestration import intervention

router = APIRouter(tags=["supervisor"])


class InterventionPayload(BaseModel):
    property_id: UUID
    reason: str | None = None
    instruction: str | None = None


@router.post("/direct-instruction")
@router.post("/direct_instruction")
def direct_instruction(payload: InterventionPayload, db: Session = Depends(get_db)) -> dict:
    result = intervention.direct_instruction(
        db, payload.property_id, payload.instruction or payload.reason or ""
    )
    db.commit()
    return intervention.to_dict(result)


@router.post("/takeover")
def takeover(payload: InterventionPayload, db: Session = Depends(get_db)) -> dict:
    result = intervention.takeover(db, payload.property_id, payload.reason or "Supervisor takeover")
    db.commit()
    return intervention.to_dict(result)


@router.post("/force-escalation")
@router.post("/force_escalation")
def force_escalation(payload: InterventionPayload, db: Session = Depends(get_db)) -> dict:
    result = intervention.force_escalation(
        db, payload.property_id, payload.reason or "Supervisor escalation"
    )
    db.commit()
    return intervention.to_dict(result)
