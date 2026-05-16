import hashlib
import hmac
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.sample_turn import run_incoming_message

router = APIRouter(tags=["webhooks"])


class WhatsAppPayload(BaseModel):
    sender_contact: str
    body: str
    thread_id: str = "whatsapp-demo"


@router.get("/whatsapp", response_class=PlainTextResponse)
def verify_whatsapp_webhook(
    mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    challenge: Annotated[str | None, Query(alias="hub.challenge")] = None,
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    expected_token = (
        settings.WHATSAPP_VERIFY_TOKEN.get_secret_value()
        if settings.WHATSAPP_VERIFY_TOKEN
        else ""
    )
    if mode == "subscribe" and verify_token and verify_token == expected_token and challenge:
        return PlainTextResponse(challenge, status_code=200)
    raise HTTPException(status_code=403, detail="WhatsApp webhook verification failed.")


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    x_hub_signature_256: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    raw_body = await request.body()
    _verify_signature(raw_body, x_hub_signature_256, settings)
    payload = await request.json()

    if "sender_contact" in payload and "body" in payload:
        return _run_internal_payload(WhatsAppPayload.model_validate(payload), db)

    results: list[dict[str, Any]] = []
    ignored: list[dict[str, str]] = []
    for message in _iter_messages(payload):
        if message.get("type") != "text":
            ignored.append(
                {
                    "message_id": str(message.get("id") or ""),
                    "reason": f"unsupported message type: {message.get('type')}",
                }
            )
            continue

        sender_contact = _normalize_contact(str(message.get("from") or ""))
        body = str(message.get("text", {}).get("body") or "").strip()
        if not sender_contact or not body:
            ignored.append(
                {
                    "message_id": str(message.get("id") or ""),
                    "reason": "missing sender or body",
                }
            )
            continue

        results.append(
            run_incoming_message(
                db=db,
                sender_contact=sender_contact,
                body=body,
                channel="whatsapp",
                thread_id=str(message.get("id") or "whatsapp-cloud"),
            )
        )

    return {"status": "received", "processed": len(results), "ignored": ignored, "results": results}


def _run_internal_payload(payload: WhatsAppPayload, db: Session) -> dict:
    result = run_incoming_message(
        db=db,
        sender_contact=payload.sender_contact,
        body=payload.body,
        channel="whatsapp",
        thread_id=payload.thread_id,
    )
    return result


def _verify_signature(
    raw_body: bytes,
    signature_header: str | None,
    settings: Settings,
) -> None:
    app_secret = (
        settings.WHATSAPP_APP_SECRET.get_secret_value()
        if settings.WHATSAPP_APP_SECRET
        else ""
    )
    if not app_secret:
        if settings.APP_ENV == "production" and settings.WHATSAPP_MODE == "cloud":
            raise HTTPException(status_code=401, detail="Missing WhatsApp app secret.")
        return

    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing WhatsApp signature.")

    expected = "sha256=" + hmac.new(
        app_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature_header, expected):
        raise HTTPException(status_code=401, detail="Invalid WhatsApp signature.")


def _iter_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages.extend(value.get("messages", []) or [])
    return messages


def _normalize_contact(value: str) -> str:
    contact = value.strip()
    if not contact:
        return ""
    if contact.startswith("+"):
        return contact
    return f"+{contact}"
