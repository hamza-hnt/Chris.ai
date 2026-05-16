from app.api.webhooks.twilio import _filename_for_media, _first_audio_media
from app.integrations.slng_stub import _encoding_from_content_type, _extract_transcript, _stt_endpoint


def test_twilio_audio_media_is_detected():
    form = {
        "NumMedia": "2",
        "MediaUrl0": "https://api.twilio.com/photo",
        "MediaContentType0": "image/jpeg",
        "MediaUrl1": "https://api.twilio.com/audio",
        "MediaContentType1": "audio/ogg",
    }

    media = _first_audio_media(form)

    assert media == {
        "index": "1",
        "url": "https://api.twilio.com/audio",
        "content_type": "audio/ogg",
    }


def test_twilio_audio_filename_uses_content_type_extension():
    assert _filename_for_media("SM/voice test", "audio/ogg") == "SMvoicetest.ogg"
    assert _filename_for_media("SMvoice", "audio/webm; codecs=opus") == "SMvoice.webm"


def test_slng_unified_api_endpoint_and_supported_encoding():
    assert (
        _stt_endpoint("slng/deepgram/nova:3-multi")
        == "https://api.slng.ai/v1/bridges/unmute/stt/slng/deepgram/nova:3-multi"
    )
    assert _encoding_from_content_type("audio/ogg") == "opus"
    assert _encoding_from_content_type("audio/webm; codecs=opus") == ""


def test_slng_transcript_extraction_supports_deepgram_and_whisper_shapes():
    assert _extract_transcript({"text": "bonjour"}) == "bonjour"
    assert (
        _extract_transcript(
            {
                "type": "transcription",
                "is_final": True,
                "alternatives": [{"confidence": 0.99, "transcript": "hello from slng"}],
            }
        )
        == "hello from slng"
    )
    assert (
        _extract_transcript(
            {
                "results": {
                    "channels": [
                        {
                            "alternatives": [
                                {"transcript": "fuite sous l'evier", "confidence": 0.98}
                            ]
                        }
                    ]
                }
            }
        )
        == "fuite sous l'evier"
    )
