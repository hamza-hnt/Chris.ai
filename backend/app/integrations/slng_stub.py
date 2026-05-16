import logging

logger = logging.getLogger("chris.integrations.slng")


def send_voice(to_role: str, body: str, attachments: list[str] | None = None) -> dict:
    payload = {
        "channel": "voice",
        "provider": "slng",
        "model_family": "slng-native-tts",
        "to_role": to_role,
        "body": body,
        "attachments": attachments or [],
    }
    logger.info("SLNG voice stub send: %s", payload)
    return {"sent": True, **payload}


def transcribe_audio(audio_ref: str) -> dict:
    payload = {
        "provider": "slng",
        "model_family": "slng-native-stt",
        "audio_ref": audio_ref,
        "text": "",
        "stub": True,
    }
    logger.info("SLNG STT stub transcribe: %s", payload)
    return payload
