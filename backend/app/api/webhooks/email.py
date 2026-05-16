from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["webhooks"])


class EmailPayload(BaseModel):
    sender_contact: str
    subject: str
    body: str


@router.post("/email")
def email_webhook(payload: EmailPayload) -> dict:
    return {
        "status": "accepted",
        "stub": True,
        "message": "Email integration is stubbed for the first build.",
        "sender_contact": payload.sender_contact,
    }
