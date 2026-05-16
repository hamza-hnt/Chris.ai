import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("chris.integrations.whatsapp")


def send_whatsapp(
    to_role: str,
    body: str,
    attachments: list[str] | None = None,
    to_phone: str | None = None,
) -> dict:
    payload = {
        "channel": "whatsapp",
        "to_role": to_role,
        "to_phone": _redact_phone(to_phone),
        "body": body,
        "attachments": attachments or [],
    }
    settings = get_settings()
    if settings.WHATSAPP_MODE == "stub":
        logger.info("WhatsApp stub send: %s", payload)
        return {"sent": True, "mode": "stub", **payload}
    if settings.WHATSAPP_MODE == "twilio":
        return _send_via_twilio(settings, to_phone, body, attachments or [], payload)

    if not to_phone:
        return {"sent": False, "mode": "cloud", "error": "missing_recipient_phone", **payload}

    token = settings.WHATSAPP_ACCESS_TOKEN.get_secret_value() if settings.WHATSAPP_ACCESS_TOKEN else ""
    url = (
        f"https://graph.facebook.com/{settings.WHATSAPP_GRAPH_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": _normalize_for_cloud(to_phone),
            "type": "text",
            "text": {"preview_url": False, "body": body},
        },
        timeout=15,
    )
    if response.status_code >= 400:
        logger.warning("WhatsApp Cloud send failed: status=%s body=%s", response.status_code, response.text)
        return {
            "sent": False,
            "mode": "cloud",
            "status_code": response.status_code,
            "error": response.text,
            **payload,
        }
    return {"sent": True, "mode": "cloud", "provider_response": response.json(), **payload}


def _send_via_twilio(settings, to_phone: str | None, body: str, attachments: list[str], payload: dict) -> dict:
    if not to_phone:
        return {"sent": False, "mode": "twilio", "error": "missing_recipient_phone", **payload}

    account_sid = settings.TWILIO_ACCOUNT_SID or ""
    auth_token = settings.TWILIO_AUTH_TOKEN.get_secret_value() if settings.TWILIO_AUTH_TOKEN else ""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    data: dict[str, str | list[str]] = {
        "From": _normalize_for_twilio(settings.TWILIO_WHATSAPP_FROM),
        "To": _normalize_for_twilio(to_phone),
        "Body": body,
    }
    if attachments:
        data["MediaUrl"] = attachments

    response = httpx.post(url, auth=(account_sid, auth_token), data=data, timeout=15)
    if response.status_code >= 400:
        logger.warning("Twilio WhatsApp send failed: status=%s body=%s", response.status_code, response.text)
        return {
            "sent": False,
            "mode": "twilio",
            "status_code": response.status_code,
            "error": response.text,
            **payload,
        }
    provider_response = response.json()
    logger.info(
        "Twilio WhatsApp send accepted: sid=%s status=%s to=%s",
        provider_response.get("sid"),
        provider_response.get("status"),
        payload["to_phone"],
    )
    return {"sent": True, "mode": "twilio", "provider_response": provider_response, **payload}


def _normalize_for_cloud(value: str) -> str:
    return value.strip().replace(" ", "")


def _normalize_for_twilio(value: str) -> str:
    clean = value.strip().replace(" ", "")
    return clean if clean.startswith("whatsapp:") else f"whatsapp:{clean}"


def _redact_phone(value: str | None) -> str | None:
    if not value:
        return None
    clean = value.strip()
    if len(clean) <= 5:
        return "***"
    return f"{clean[:3]}***{clean[-2:]}"
