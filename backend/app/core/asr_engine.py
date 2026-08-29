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


def engine_status() -> dict:
    """Return status dict for /api/asr/status endpoint."""
    engine = active_engine()
    return {
        "engine": engine,
        "available": engine != "stub",
        "model": WHISPER_MODEL if engine == "faster-whisper" else None,
    }


def suffix_for_content_type(content_type: str | None) -> str:
    """Determine file suffix from content type for temp file."""
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        if "webm" in ct:
            return ".webm"
        if "ogg" in ct:
            return ".ogg"
        if "wav" in ct:
            return ".wav"
        if "mp4" in ct or "m4a" in ct:
            return ".m4a"
    return ".webm"


def suffix_for_bytes(data: bytes, content_type: str | None = None) -> str:
    """Detect file extension by inspecting magic bytes or content type."""
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return ".webm"
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WAVE":
        return ".wav"
    if data.startswith(b"OggS"):
        return ".ogg"
    if data.startswith(b"\xff\xfb") or data.startswith(b"\xff\xf3") or data.startswith(b"ID3"):
        return ".mp3"
    return suffix_for_content_type(content_type)


def _is_hallucination(text: str) -> bool:
    """Detect typical Whisper hallucinations on silent/noisy audio."""
    t = text.strip().lower()
    if not t or len(t) <= 3 and set(t).issubset({".", " ", "-", "♪"}):
        return True
    hallucination_phrases = {
        "thank you.", "thank you very much.", "thanks for watching!",
        "subtitles by amara.org", "subtitles by the amara.org community",
        "you", "bye.", "subscribe", "please subscribe",
    }
    if t in hallucination_phrases or all(c in "♪♩ ♫" for c in t):
        return True
    return False



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


def warmup() -> None:
    """Pre-load the Whisper model on startup to avoid timeout on first request."""
    if not _should_run_whisper():
        return
    try:
        _whisper_model()
        logger.info("Whisper model warmed up successfully")
    except Exception:
        logger.exception("Whisper model warmup failed")



def transcribe_audio(data: bytes, language: str = "en", content_type: str | None = None) -> dict:
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
        segments_iter, info = model.transcribe(tmp_path, language=lang, vad_filter=True)
        segments = list(segments_iter)
        transcript = " ".join((s.text or "").strip() for s in segments).strip()
        confidence = _confidence_from_segments(segments) if transcript else 0.0
        duration_ms = int(info.duration * 1000) if info else len(data) // 32  # fallback estimate
        return {
            "transcript": transcript,
            "confidence": confidence,
            "language": language,
            "engine": "faster-whisper",
            "duration_ms": duration_ms,
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
