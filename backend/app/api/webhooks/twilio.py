import base64
import hashlib
import hmac
from typing import Annotated
from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.sample_turn import run_incoming_message

router = APIRouter(tags=["webhooks"])


@router.post("/twilio/whatsapp")
async def twilio_whatsapp_webhook(
    request: Request,
    x_twilio_signature: Annotated[str | None, Header(alias="X-Twilio-Signature")] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    raw_body = await request.body()
    form = dict(parse_qsl(raw_body.decode("utf-8"), keep_blank_values=True))
    _verify_twilio_signature(request, form, x_twilio_signature, settings)

    from_contact = _normalize_twilio_whatsapp_address(form.get("From", ""))
    body = (form.get("Body") or "").strip()
    message_sid = form.get("MessageSid") or form.get("SmsMessageSid") or "twilio-whatsapp"

    if not from_contact:
        raise HTTPException(status_code=400, detail="Twilio webhook is missing From.")
    if not body:
        return {
            "status": "ignored",
            "reason": "empty_body_or_unsupported_message",
            "message_sid": message_sid,
        }

    result = run_incoming_message(
        db=db,
        sender_contact=from_contact,
        body=body,
        channel="whatsapp",
        thread_id=message_sid,
    )
    return {"status": "received", "provider": "twilio", "message_sid": message_sid, "result": result}


def _verify_twilio_signature(
    request: Request,
    form: dict[str, str],
    signature_header: str | None,
    settings: Settings,
) -> None:
    should_validate = settings.TWILIO_VALIDATE_SIGNATURE or settings.APP_ENV == "production"
    if not should_validate:
        return

    auth_token = settings.TWILIO_AUTH_TOKEN.get_secret_value() if settings.TWILIO_AUTH_TOKEN else ""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Missing Twilio auth token.")
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing Twilio signature.")

    url = str(request.url)
    payload = url + "".join(key + value for key, value in sorted(form.items()))
    digest = hmac.new(auth_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1).digest()
    expected = base64.b64encode(digest).decode("ascii")
    if not hmac.compare_digest(signature_header, expected):
        raise HTTPException(status_code=401, detail="Invalid Twilio signature.")


def _normalize_twilio_whatsapp_address(value: str) -> str:
    address = value.strip()
    if address.startswith("whatsapp:"):
        address = address.removeprefix("whatsapp:")
    return address if address.startswith("+") else f"+{address}" if address else ""
