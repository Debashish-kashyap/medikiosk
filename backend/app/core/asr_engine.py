"""Optional speech-to-text engine (Lane 4).

Default path is a no-op stub so the demo stays keyless and `pytest` never
downloads a model. Set MEDIKIOSK_ASR=bhashini and install bhashini to
transcribe uploaded audio locally with Indian language support.

The kiosk still uses the browser Web Speech API by default; this engine is
the production seam for Chrome-less / offline kiosks.

Bhashini (Google's Indic ASR) is the primary engine for Indian languages.
faster-whisper serves as a fallback for English and other languages.
"""
from __future__ import annotations

import logging
import os
import tempfile
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

# ASR_MODE: bhashini | whisper | stub | auto
ASR_MODE = os.getenv("MEDIKIOSK_ASR", "").strip().lower()
WHISPER_MODEL = os.getenv("MEDIKIOSK_WHISPER_MODEL", "tiny")

# Supported languages for each engine
BHASHINI_LANGS = {
    "en": "en", "hi": "hi", "mr": "mr", "ta": "ta", "te": "te",
    "bn": "bn", "gu": "gu", "kn": "kn", "ml": "ml", "pa": "pa",
    "or": "or", "as": "as", "ur": "ur", "sd": "sd"
}
WHISPER_LANGS = {"en": "en", "hi": "hi", "mr": "mr", "ta": "ta", "bn": "bn"}


def bhashini_available() -> bool:
    """Check if Bhashini ASR is available."""
    try:
        import bhashini  # noqa: F401
        return True
    except ImportError:
        return False


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
    if mode == "bhashini":
        return "bhashini" if bhashini_available() else "stub"
    if mode == "whisper":
        return "faster-whisper" if whisper_available() else "stub"
    if mode == "auto":
        if bhashini_available():
            return "bhashini"
        if whisper_available():
            return "faster-whisper"
        return "stub"
    return "stub"


def engine_status() -> dict:
    """Return status dict for /api/asr/status endpoint."""
    engine = active_engine()
    if engine == "bhashini":
        return {
            "engine": "bhashini",
            "available": True,
            "model": "bhashini-indic-asr",
            "supported_languages": list(BHASHINI_LANGS.keys()),
        }
    if engine == "faster-whisper":
        return {
            "engine": "faster-whisper",
            "available": True,
            "model": WHISPER_MODEL,
            "supported_languages": list(WHISPER_LANGS.keys()),
        }
    return {
        "engine": "stub",
        "available": False,
        "model": None,
        "supported_languages": [],
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
    """Detect typical ASR hallucinations on silent/noisy audio."""
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


def _should_run_bhashini() -> bool:
    if ASR_MODE in {"stub", "off", "0", "false"}:
        return False
    if ASR_MODE == "bhashini":
        return bhashini_available()
    # auto: use bhashini if available
    return bhashini_available()


def _should_run_whisper() -> bool:
    if ASR_MODE in {"stub", "off", "0", "false"}:
        return False
    if ASR_MODE == "whisper":
        return whisper_available()
    # auto: use whisper only if bhashini not available
    return not bhashini_available() and whisper_available()


# Bhashini initialization (single instance)
_bh_model = None


def _get_bhashini_model():
    """Initialize and cache Bhashini ASR model."""
    global _bh_model
    if _bh_model is not None:
        return _bh_model

    try:
        from bhashini.asr import ASR

        # Initialize Bhashini with default model
        _bh_model = ASR()
        logger.info("Bhashini ASR model initialized successfully")
        return _bh_model
    except Exception as e:
        logger.error("Bhashini ASR initialization failed: %s", e)
        _bh_model = None
        return None


# Whisper model caching
@lru_cache(maxsize=1)
def _whisper_model():
    from faster_whisper import WhisperModel
    return WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")


def _confidence_from_segments(segments: list[Any], engine: str = "whisper") -> float:
    """Calculate confidence score from ASR segments."""
    if not segments:
        return 0.0

    scores: list[float] = []

    if engine == "bhashini":
        # Bhashini returns confidence per segment
        for seg in segments:
            conf = float(getattr(seg, "confidence", 0.5) or 0.5)
            scores.append(conf)
    else:
        # Whisper-style scoring (default for backward compatibility)
        for seg in segments:
            logprob = float(getattr(seg, "avg_logprob", -1.0) or -1.0)
            no_speech = float(getattr(seg, "no_speech_prob", 0.5) or 0.5)
            from_logprob = max(0.0, min(1.0, 1.0 + logprob / 1.5))
            from_speech = max(0.0, min(1.0, 1.0 - no_speech))
            scores.append(0.4 * from_logprob + 0.6 * from_speech)

    return round(sum(scores) / len(scores), 3) if scores else 0.0


def warmup() -> None:
    """Pre-load models on startup to avoid timeout on first request."""
    if _should_run_bhashini():
        try:
            _get_bhashini_model()
            logger.info("Bhashini model warmed up successfully")
        except Exception:
            logger.exception("Bhashini model warmup failed")

    if _should_run_whisper():
        try:
            _whisper_model()
            logger.info("Whisper model warmed up successfully")
        except Exception:
            logger.exception("Whisper model warmup failed")


def transcribe_with_bhashini(data: bytes, language: str) -> dict:
    """Transcribe audio using Bhashini ASR."""
    model = _get_bhashini_model()
    if model is None:
        raise RuntimeError("Bhashini model not available")

    suffix = suffix_for_bytes(data)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        # Bhashini transcribe returns results with text and confidence
        result = model.transcribe(tmp_path, lang=language)
        transcript = result.get("text", "") if isinstance(result, dict) else str(result)

        if isinstance(result, dict):
            confidence = float(result.get("confidence", 0.5))
        else:
            confidence = 0.75  # Default confidence for text-only response

        duration_ms = result.get("duration_ms", 0) if isinstance(result, dict) else 0

        return {
            "transcript": transcript,
            "confidence": confidence,
            "language": language,
            "engine": "bhashini",
            "duration_ms": duration_ms,
        }
    except Exception:
        logger.exception("Bhashini transcription failed")
        raise
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def transcribe_with_whisper(data: bytes, language: str) -> dict:
    """Transcribe audio using faster-whisper (fallback)."""
    lang = WHISPER_LANGS.get((language or "en").split("-")[0], "en")
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
        confidence = _confidence_from_segments(segments, engine="whisper") if transcript else 0.0
        duration_ms = int(info.duration * 1000) if info else 0
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


def transcribe_audio(data: bytes, language: str = "en", content_type: str | None = None) -> dict:
    """Transcribe raw audio bytes using best available engine.

    Priority:
    1. Bhashini (for Indian languages and better accuracy on Indian accent)
    2. Faster-whisper (fallback)
    3. Stub (no engine available)
    """
    if not data:
        return {"transcript": "", "confidence": 0.0, "language": language, "engine": active_engine()}

    # Try Bhashini first (primary engine for Indian languages)
    if _should_run_bhashini():
        try:
            logger.info("Transcribing with Bhashini ASR, language=%s", language)
            return transcribe_with_bhashini(data, language)
        except ImportError:
            logger.info("Bhashini not installed; falling back to whisper")
        except Exception as e:
            logger.warning("Bhashini failed (%s); falling back to whisper", e)

    # Fallback to whisper
    if _should_run_whisper():
        try:
            logger.info("Transcribing with faster-whisper, language=%s", language)
            return transcribe_with_whisper(data, language)
        except Exception:
            logger.exception("Whisper transcription failed")

    # No engine available
    return {
        "transcript": "",
        "confidence": 0.0,
        "language": language,
        "engine": "stub",
        "note": "Stub ASR — set MEDIKIOSK_ASR=bhashini and install bhashini, or use whisper.",
    }
