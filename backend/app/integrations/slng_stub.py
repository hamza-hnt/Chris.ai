import logging
from typing import Any

import httpx

from app.config import Settings, get_settings

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


def transcribe_audio_bytes(
    audio: bytes,
    content_type: str,
    filename: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Transcribe an inbound audio file through SLNG's HTTP STT API."""
    resolved_settings = settings or get_settings()
    api_key = (
        resolved_settings.SLNG_API_KEY.get_secret_value()
        if resolved_settings.SLNG_API_KEY
        else ""
    )
    if not api_key:
        return {
            "ok": False,
            "provider": "slng",
            "error": "missing_slng_api_key",
        }

    endpoint = _stt_endpoint(resolved_settings.SLNG_STT_MODEL)
    data: dict[str, str] = {}
    language = _language_for_model(resolved_settings.SLNG_STT_MODEL)
    if language:
        data["language"] = language
    encoding = _encoding_from_content_type(content_type)
    if encoding:
        data["encoding"] = encoding

    try:
        response = httpx.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}"},
            data=data,
            files={"audio": (filename, audio, content_type or "application/octet-stream")},
            timeout=60,
        )
    except httpx.HTTPError as exc:
        logger.warning("SLNG STT request failed: %s", exc)
        return {
            "ok": False,
            "provider": "slng",
            "model": resolved_settings.SLNG_STT_MODEL,
            "error": str(exc),
        }

    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text}

    if response.status_code >= 400:
        logger.warning(
            "SLNG STT refused audio: status=%s content_type=%s body=%s",
            response.status_code,
            content_type,
            payload,
        )
        return {
            "ok": False,
            "provider": "slng",
            "model": resolved_settings.SLNG_STT_MODEL,
            "status_code": response.status_code,
            "error": payload,
        }

    text = _extract_transcript(payload).strip()
    return {
        "ok": bool(text),
        "provider": "slng",
        "model": resolved_settings.SLNG_STT_MODEL,
        "text": text,
        "language": payload.get("language") if isinstance(payload, dict) else None,
        "content_type": content_type,
        "filename": filename,
        "raw": payload,
    }


def _stt_endpoint(model: str) -> str:
    clean = model.strip()
    if clean.startswith("http://") or clean.startswith("https://"):
        return clean
    return f"https://api.slng.ai/v1/bridges/unmute/stt/{clean.strip('/')}"


def _language_for_model(model: str) -> str:
    clean = model.strip().lower()
    if clean.endswith("-en"):
        return "en"
    if clean.endswith("-es"):
        return "es"
    if clean.endswith("-fr"):
        return "fr"
    if clean.endswith("-hi"):
        return "hi"
    return ""


def _encoding_from_content_type(content_type: str) -> str:
    clean = content_type.split(";", 1)[0].strip().lower()
    return {
        "audio/ogg": "opus",
        "audio/opus": "opus",
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/wav": "linear16",
        "audio/x-wav": "linear16",
    }.get(clean, "")


def _extract_transcript(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""

    direct = payload.get("text") or payload.get("transcript")
    if isinstance(direct, str):
        return direct

    alternatives = payload.get("alternatives")
    if isinstance(alternatives, list):
        for alternative in alternatives:
            if isinstance(alternative, dict) and isinstance(alternative.get("transcript"), str):
                return alternative["transcript"]

    results = payload.get("results")
    if isinstance(results, dict):
        channels = results.get("channels")
        if isinstance(channels, list):
            for channel in channels:
                if not isinstance(channel, dict):
                    continue
                alternatives = channel.get("alternatives")
                if not isinstance(alternatives, list):
                    continue
                for alternative in alternatives:
                    if isinstance(alternative, dict) and isinstance(
                        alternative.get("transcript"), str
                    ):
                        return alternative["transcript"]

        utterances = results.get("utterances")
        if isinstance(utterances, list):
            parts = [
                utterance.get("transcript", "")
                for utterance in utterances
                if isinstance(utterance, dict)
            ]
            return " ".join(part.strip() for part in parts if part.strip())

    return ""
