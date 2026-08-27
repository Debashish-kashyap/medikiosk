"""Speech-to-text endpoint (Module A voice path).

The kiosk frontend uses the browser Web Speech API by default (zero setup).
This endpoint is the production seam: Lane 4 wires faster-whisper here.
Set MEDIKIOSK_ASR=whisper (and pip install faster-whisper) to transcribe
uploaded audio; mock_text still works so the pipeline is testable without a mic.
"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from ..core.asr_engine import active_engine, transcribe_audio

router = APIRouter(prefix="/api", tags=["asr"])


@router.post("/asr")
async def transcribe(
    audio: UploadFile | None = File(default=None),
    mock_text: str | None = Form(default=None),
    language: str = Form(default="en"),
) -> dict:
    # Lets you test the rest of the pipeline without a microphone.
    if mock_text is not None:
        return {
            "transcript": mock_text,
            "confidence": 0.9,
            "language": language,
            "engine": "mock",
        }

    if audio is None:
        return {
            "transcript": "",
            "confidence": 0.0,
            "language": language,
            "engine": active_engine(),
            "note": "No audio uploaded.",
        }

    data = await audio.read()
    return transcribe_audio(data, language)
