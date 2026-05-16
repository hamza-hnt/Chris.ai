import logging

logger = logging.getLogger("chris.integrations.whatsapp")


def send_whatsapp(to_role: str, body: str, attachments: list[str] | None = None) -> dict:
    payload = {"channel": "whatsapp", "to_role": to_role, "body": body, "attachments": attachments or []}
    logger.info("WhatsApp stub send: %s", payload)
    return {"sent": True, **payload}
