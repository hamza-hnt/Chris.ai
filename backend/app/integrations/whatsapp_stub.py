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


def _normalize_for_cloud(value: str) -> str:
    return value.strip().replace(" ", "")


def _redact_phone(value: str | None) -> str | None:
    if not value:
        return None
    clean = value.strip()
    if len(clean) <= 5:
        return "***"
    return f"{clean[:3]}***{clean[-2:]}"
