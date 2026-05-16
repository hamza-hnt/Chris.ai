import base64
import hashlib
import hmac
import logging
from typing import Annotated
from urllib.parse import parse_qsl

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.integrations.slng_stub import transcribe_audio_bytes
from app.sample_turn import run_incoming_message

router = APIRouter(tags=["webhooks"])
logger = logging.getLogger("chris.webhooks.twilio")


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
    audio_media = _first_audio_media(form)
    transcription: dict | None = None
    channel = "whatsapp"

    if not from_contact:
        raise HTTPException(status_code=400, detail="Twilio webhook is missing From.")
    if not body:
        if audio_media:
            transcription = _transcribe_twilio_audio(audio_media, message_sid, settings)
            if transcription.get("ok") and transcription.get("text"):
                body = str(transcription["text"]).strip()
                channel = "voice"
                logger.info(
                    "Twilio voice message transcribed: sid=%s content_type=%s chars=%s",
                    message_sid,
                    audio_media.get("content_type"),
                    len(body),
                )
            else:
                logger.warning(
                    "Ignoring Twilio voice message after transcription failure: sid=%s reason=%s",
                    message_sid,
                    transcription.get("error") if transcription else "unknown",
                )
                return {
                    "status": "ignored",
                    "reason": "audio_transcription_failed",
                    "message_sid": message_sid,
                    "media_content_type": audio_media.get("content_type"),
                }

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
        channel=channel,
        thread_id=message_sid,
    )
    response: dict = {
        "status": "received",
        "provider": "twilio",
        "message_sid": message_sid,
        "channel": channel,
        "result": result,
    }
    if transcription:
        response["transcription"] = {
            "provider": transcription.get("provider"),
            "model": transcription.get("model"),
            "content_type": transcription.get("content_type"),
            "text_chars": len(body),
        }
    return response


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


def _first_audio_media(form: dict[str, str]) -> dict[str, str] | None:
    try:
        count = int(form.get("NumMedia", "0") or "0")
    except ValueError:
        count = 0

    for index in range(count):
        media_url = form.get(f"MediaUrl{index}", "").strip()
        content_type = form.get(f"MediaContentType{index}", "").strip()
        if media_url and content_type.lower().startswith("audio/"):
            return {
                "index": str(index),
                "url": media_url,
                "content_type": content_type,
            }
    return None


def _transcribe_twilio_audio(
    media: dict[str, str],
    message_sid: str,
    settings: Settings,
) -> dict:
    audio = _download_twilio_media(media["url"], settings)
    filename = _filename_for_media(message_sid, media.get("content_type", ""))
    return transcribe_audio_bytes(
        audio=audio,
        content_type=media.get("content_type", ""),
        filename=filename,
        settings=settings,
    )


def _download_twilio_media(media_url: str, settings: Settings) -> bytes:
    account_sid = settings.TWILIO_ACCOUNT_SID or ""
    auth_token = settings.TWILIO_AUTH_TOKEN.get_secret_value() if settings.TWILIO_AUTH_TOKEN else ""
    response = httpx.get(
        media_url,
        auth=(account_sid, auth_token),
        timeout=30,
        follow_redirects=True,
    )
    if response.status_code >= 400:
        logger.warning("Twilio media download failed: status=%s body=%s", response.status_code, response.text)
        raise HTTPException(status_code=502, detail="Could not download Twilio media.")
    return response.content


def _filename_for_media(message_sid: str, content_type: str) -> str:
    extension = _extension_from_content_type(content_type)
    safe_sid = "".join(char for char in message_sid if char.isalnum() or char in {"-", "_"}) or "twilio"
    return f"{safe_sid}{extension}"


def _extension_from_content_type(content_type: str) -> str:
    clean = content_type.split(";", 1)[0].strip().lower()
    return {
        "audio/ogg": ".ogg",
        "audio/opus": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/m4a": ".m4a",
        "audio/webm": ".webm",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/flac": ".flac",
    }.get(clean, ".audio")
