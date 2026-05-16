import logging

logger = logging.getLogger("chris.integrations.email")


def send_email(to_role: str, body: str, attachments: list[str] | None = None) -> dict:
    payload = {"channel": "email", "to_role": to_role, "body": body, "attachments": attachments or []}
    logger.info("Email stub send: %s", payload)
    return {"sent": True, **payload}
