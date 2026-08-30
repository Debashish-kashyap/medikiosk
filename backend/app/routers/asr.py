"""Lane 4: ASR endpoint — POST /api/asr and GET /api/asr/status."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from ..core.asr_engine import active_engine, engine_status, transcribe_audio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["asr"])

_TRANSCRIBE_TIMEOUT = 90  # seconds before we give up and return empty


@router.get("/asr/status")
async def asr_status() -> dict:
    """Return current ASR engine info (used by VoiceButton on mount)."""
    return engine_status()


@router.post("/asr")
async def transcribe(
    audio: Optional[UploadFile] = File(default=None),
    mock_text: Optional[str] = Form(default=None),
    language: str = Form(default="en"),
) -> dict:
    """Transcribe speech audio or echo mock_text for testing.

    Accepts multipart/form-data with:
      - audio: audio blob (webm, wav, ogg, m4a, mp3)
      - language: BCP-47 tag (en, hi, mr, …)
      - mock_text: bypass ASR and return this string directly (testing only)
    """
    # --- Mock / testing bypass ---
    if mock_text is not None:
        return {
            "transcript": mock_text,
            "confidence": 0.9,
            "language": language,
            "engine": "mock",
        }

    # --- No audio provided ---
    if audio is None:
        return {
            "transcript": "",
            "confidence": 0.0,
            "language": language,
            "engine": active_engine(),
            "note": "no audio payload received",
        }

    # --- Real transcription ---
    try:
        data = await audio.read()
        logger.info(
            "ASR request: %d bytes, content_type=%s, lang=%s, first_bytes=%s",
            len(data),
            audio.content_type,
            language,
            data[:8].hex() if data else "empty",
        )

        result = await asyncio.wait_for(
            asyncio.to_thread(
                transcribe_audio, data, language, audio.content_type
            ),
            timeout=_TRANSCRIBE_TIMEOUT,
        )
        return result

    except asyncio.TimeoutError:
        logger.warning("ASR timed out after %ds", _TRANSCRIBE_TIMEOUT)
        return {
            "transcript": "",
            "confidence": 0.0,
            "language": language,
            "engine": active_engine(),
            "note": f"ASR timed out after {_TRANSCRIBE_TIMEOUT}s",
        }
    except Exception:
        logger.exception("Unexpected ASR error")
        return {
            "transcript": "",
            "confidence": 0.0,
            "language": language,
            "engine": active_engine(),
            "note": "internal ASR error — check server logs",
        }
