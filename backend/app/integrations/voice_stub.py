import logging

logger = logging.getLogger("chris.integrations.voice")


def send_voice(to_role: str, body: str, attachments: list[str] | None = None) -> dict:
    payload = {"channel": "voice", "to_role": to_role, "body": body, "attachments": attachments or []}
    logger.info("Voice stub send: %s", payload)
    return {"sent": True, **payload}
