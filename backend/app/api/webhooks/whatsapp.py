from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.sample_turn import run_incoming_message

router = APIRouter(tags=["webhooks"])


class WhatsAppPayload(BaseModel):
    sender_contact: str
    body: str
    thread_id: str = "whatsapp-demo"


@router.post("/whatsapp")
def whatsapp_webhook(payload: WhatsAppPayload, db: Session = Depends(get_db)) -> dict:
    result = run_incoming_message(
        db=db,
        sender_contact=payload.sender_contact,
        body=payload.body,
        channel="whatsapp",
        thread_id=payload.thread_id,
    )
    return result
