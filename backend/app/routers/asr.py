"""Speech-to-text endpoint (Module A voice path).

DEMO NOTE: the kiosk frontend uses the browser Web Speech API for live voice, so the
demo works with zero setup. THIS endpoint is the production seam: the AI-Speech lane
wires faster-whisper (offline) or Bhashini/AI4Bharat (Indian languages) here, adding
noise suppression + voice-activity-detection before ASR, and returns a real confidence
score that drives the kiosk's confirm/repeat logic.
"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

router = APIRouter(prefix="/api", tags=["asr"])


@router.post("/asr")
async def transcribe(
    audio: UploadFile | None = File(default=None),
    mock_text: str | None = Form(default=None),
    language: str = Form(default="en"),
) -> dict:
    # --- PRODUCTION (AI-Speech lane) --------------------------------------
    # data = await audio.read()
    # transcript, confidence = whisper_or_bhashini(data, language)
    # return {"transcript": transcript, "confidence": confidence, "language": language}
    # ----------------------------------------------------------------------
    if mock_text is not None:                      # lets you test the pipeline without audio
        return {"transcript": mock_text, "confidence": 0.9, "language": language}
    if audio is not None:
        await audio.read()
    return {
        "transcript": "",
        "confidence": 0.0,
        "language": language,
        "note": "Stub ASR — wire faster-whisper / Bhashini here.",
    }
