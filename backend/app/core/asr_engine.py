"""Optional speech-to-text engine (Lane 4).

Default path is a no-op stub so the demo stays keyless and `pytest` never
downloads a model. Set MEDIKIOSK_ASR=whisper and `pip install faster-whisper`
to transcribe uploaded audio locally (offline, no API key).

The kiosk still uses the browser Web Speech API by default; this engine is
the production seam for Chrome-less / offline kiosks.
"""
from __future__ import annotations

import logging
import os
import tempfile
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

# whisper | stub | auto (use whisper if the package is importable)
ASR_MODE = os.getenv("MEDIKIOSK_ASR", "").strip().lower()
WHISPER_MODEL = os.getenv("MEDIKIOSK_WHISPER_MODEL", "tiny")

_WHISPER_LANG = {"en": "en", "hi": "hi", "mr": "mr", "ta": "ta"}


def whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401

        return True
    except ImportError:
        return False


def active_engine() -> str:
    """Name reported in /health and ASR responses."""
    mode = ASR_MODE or "auto"
    if mode in {"stub", "off", "0", "false"}:
        return "stub"
    if mode == "whisper" or mode == "auto":
        return "faster-whisper" if whisper_available() else "stub"
    return "stub"


def _should_run_whisper() -> bool:
    if ASR_MODE in {"stub", "off", "0", "false"}:
        return False
    if ASR_MODE == "whisper":
        return whisper_available()
    # auto / unset: use whisper only if already installed (never force a pip dep)
    return whisper_available()


@lru_cache(maxsize=1)
def _whisper_model():
    from faster_whisper import WhisperModel

    # CPU + int8 keeps a kiosk laptop usable; tiny/base is enough for demo.
    return WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")


def _confidence_from_segments(segments: list[Any]) -> float:
    if not segments:
        return 0.0
    scores: list[float] = []
    for seg in segments:
        logprob = float(getattr(seg, "avg_logprob", -1.0) or -1.0)
        no_speech = float(getattr(seg, "no_speech_prob", 0.5) or 0.5)
        from_logprob = max(0.0, min(1.0, 1.0 + logprob / 1.5))
        from_speech = max(0.0, min(1.0, 1.0 - no_speech))
        scores.append(0.4 * from_logprob + 0.6 * from_speech)
    return round(sum(scores) / len(scores), 3)


def transcribe_audio(data: bytes, language: str = "en") -> dict:
    """Transcribe raw audio bytes. Always returns the ASR contract dict."""
    lang = _WHISPER_LANG.get((language or "en").split("-")[0], "en")
    if not data:
        return {"transcript": "", "confidence": 0.0, "language": language, "engine": active_engine()}

    if not _should_run_whisper():
        return {
            "transcript": "",
            "confidence": 0.0,
            "language": language,
            "engine": "stub",
            "note": "Stub ASR — set MEDIKIOSK_ASR=whisper and pip install faster-whisper.",
        }

    suffix = ".webm"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        model = _whisper_model()
        segments_iter, _info = model.transcribe(tmp_path, language=lang, vad_filter=True)
        segments = list(segments_iter)
        transcript = " ".join((s.text or "").strip() for s in segments).strip()
        confidence = _confidence_from_segments(segments) if transcript else 0.0
        return {
            "transcript": transcript,
            "confidence": confidence,
            "language": language,
            "engine": "faster-whisper",
        }
    except Exception:
        logger.exception("faster-whisper transcription failed")
        return {
            "transcript": "",
            "confidence": 0.0,
            "language": language,
            "engine": "faster-whisper",
            "note": "ASR failed — check ffmpeg is installed and the audio format is supported.",
        }
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
