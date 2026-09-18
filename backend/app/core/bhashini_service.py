"""Server-side Bhashini ASR and TTS adapter.

Credentials are read only from backend environment variables. This module never
returns or logs credential values and returns None when Bhashini is not configured.
"""
from __future__ import annotations

import base64
from typing import Any

import httpx

from ..config import settings

_PIPELINE_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"


def configured() -> bool:
    return bool(settings.BHASHINI_API_KEY)


def status() -> dict[str, Any]:
    missing = []
    if not settings.BHASHINI_API_KEY:
        missing.append("BHASHINI_API_KEY")
    if not settings.BHASHINI_ASR_SERVICE_ID:
        missing.append("BHASHINI_ASR_SERVICE_ID")
    if not settings.BHASHINI_TTS_SERVICE_ID:
        missing.append("BHASHINI_TTS_SERVICE_ID")
    return {
        "configured": configured(),
        "provider": "bhashini" if configured() else None,
        "asr_enabled": bool(settings.BHASHINI_ASR_SERVICE_ID),
        "tts_enabled": bool(settings.BHASHINI_TTS_SERVICE_ID),
        "ready": not missing,
        "missing": missing,
    }


def transcribe(audio: bytes, language: str, content_type: str | None = None) -> dict[str, Any] | None:
    if not configured() or not settings.BHASHINI_ASR_SERVICE_ID:
        return None
    encoded = base64.b64encode(audio).decode("ascii")
    payload = {
        "pipelineTasks": [{
            "taskType": "asr",
            "config": {
                "language": {"sourceLanguage": _language_code(language)},
                "serviceId": settings.BHASHINI_ASR_SERVICE_ID,
                "audioFormat": content_type or "audio/webm",
                "samplingRate": 16000,
            },
        }],
        "inputData": {"audio": [{"audioContent": encoded}]},
    }
    response = _post(payload)
    output = response.get("pipelineResponse", [{}])[0].get("output", [{}])[0]
    transcript = output.get("source") or output.get("transcript") or ""
    return {
        "transcript": transcript,
        "confidence": float(output.get("confidence", 0.0) or 0.0),
        "language": language,
        "engine": "bhashini",
    }


def synthesize(text: str, language: str) -> bytes | None:
    if not configured() or not settings.BHASHINI_TTS_SERVICE_ID:
        return None
    payload = {
        "pipelineTasks": [{
            "taskType": "tts",
            "config": {
                "language": {"sourceLanguage": _language_code(language)},
                "serviceId": settings.BHASHINI_TTS_SERVICE_ID,
                "gender": settings.BHASHINI_TTS_GENDER,
            },
        }],
        "inputData": {"input": [{"source": text}]},
    }
    response = _post(payload)
    output = response.get("pipelineResponse", [{}])[0].get("audio", [{}])[0]
    audio_content = output.get("audioContent")
    return base64.b64decode(audio_content) if audio_content else None


def _post(payload: dict[str, Any]) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "ulcaApiKey": settings.BHASHINI_API_KEY,
    }
    if settings.BHASHINI_USER_ID:
        headers["userID"] = settings.BHASHINI_USER_ID
    if settings.BHASHINI_INFERENCE_KEY:
        headers["Authorization"] = settings.BHASHINI_INFERENCE_KEY
    response = httpx.post(_PIPELINE_URL, json=payload, headers=headers, timeout=60.0)
    if response.is_error:
        try:
            detail = response.json().get("detail", {})
            message = detail.get("message", "Bhashini request failed") if isinstance(detail, dict) else str(detail)
        except ValueError:
            message = "Bhashini request failed"
        raise RuntimeError(f"Bhashini provider error ({response.status_code}): {message}")
    return response.json()


def _language_code(language: str) -> str:
    return (language or "en").split("-")[0].lower()
