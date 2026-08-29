"""Speech-to-text endpoint (Module A voice path).

Lane 4 — production-ready ASR router.

- ``POST /api/asr`` — transcribe audio (faster-whisper) or mock text.
- ``GET  /api/asr/status`` — check which engine is active (frontend auto-detect).

The kiosk frontend uses the browser Web Speech API by default (zero setup).
This endpoint is the production seam: faster-whisper runs here when enabled.
Set ``MEDIKIOSK_ASR=whisper`` (and ``pip install faster-whisper``) to transcribe
uploaded audio; ``mock_text`` still works so the pipeline is testable without a mic.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from ..core.asr_engine import active_engine, engine_status, suffix_for_content_type, transcribe_audio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["asr"])

# First load of a Whisper model on CPU can exceed 30s; keep this generous.
_TRANSCRIBE_TIMEOUT = 90


@router.get("/asr/status")
async def asr_status() -> dict:
    """Frontend calls this on mount to decide whether to use server ASR.

    Returns the active engine name and whether real ASR is available.
    The frontend auto-enables the MediaRecorder path if ``available`` is true.
    """
    return engine_status()


@router.post("/asr")
async def transcribe(
    audio: Optional[UploadFile] = File(default=None),
    mock_text: Optional[str] = Form(default=None),
    language: str = Form(default="en"),
) -> dict:
    """Transcribe uploaded audio or return a mock transcript.

    Priority:
    1. If ``mock_text`` is provided, echo it back (pipeline testing without a mic).
    2. If ``audio`` is uploaded, run through the ASR engine (faster-whisper / stub).
    3. If neither, return an empty result with a note.
    """
    # --- Mock path (pipeline testing) ---
    if mock_text is not None:
        return {
            "transcript": mock_text,
            "confidence": 0.9,
            "language": language,
            "engine": "mock",
        }

    # --- No audio uploaded ---
    if audio is None:
        return {
            "transcript": "",
            "confidence": 0.0,
            "language": language,
            "engine": active_engine(),
            "note": "No audio uploaded.",
        }

    # --- Real transcription path ---
    data = await audio.read()
    content_type = audio.content_type
    logger.info(
        "ASR request: filename=%s content_type=%s bytes=%d language=%s",
        audio.filename, content_type, len(data), language,
    )

    # Run in a thread so we don't block the event loop.
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(transcribe_audio, data, language, content_type),
            timeout=_TRANSCRIBE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.warning("ASR transcription timed out after %ds", _TRANSCRIBE_TIMEOUT)
        return {
            "transcript": "",
            "confidence": 0.0,
            "language": language,
            "engine": active_engine(),
            "note": f"Transcription timed out after {_TRANSCRIBE_TIMEOUT}s.",
        }
    except Exception:
        logger.exception("ASR transcription error")
        return {
            "transcript": "",
            "confidence": 0.0,
            "language": language,
            "engine": active_engine(),
            "note": "Internal ASR error.",
        }

    logger.info("ASR result: transcript=%r confidence=%.2f engine=%s", result.get("transcript"), result.get("confidence", 0), result.get("engine"))

    return result
