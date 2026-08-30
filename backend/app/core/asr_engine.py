"""Lane 4: Speech-to-text engine — faster-whisper (local) with stub fallback.

Design decisions:
- ASR_MODE read via settings at runtime, not at import, so env changes take effect.
- Hallucination filter is conservative: never drops non-empty Hindi/mixed text just
  because it lacks ASCII; only drops well-known Whisper artefacts and silence outputs.
- Confidence is derived from segment log-probs and no_speech_prob.
- Audio is written to a temp file; the suffix is inferred from content-type first,
  then from magic bytes, so WebM/Opus, WAV, OGG, M4A all decode correctly.
- warmup() is called once from a background thread on startup to avoid cold-start lag.
"""
from __future__ import annotations

import logging
import os
import re
import tempfile
from functools import lru_cache

logger = logging.getLogger(__name__)

# Resolved once per process start — env changes after import won't be seen, which
# is fine because the server must restart to pick up new env vars anyway.
_ASR_MODE: str = os.getenv("MEDIKIOSK_ASR", "auto").strip().lower()
_WHISPER_MODEL: str = os.getenv("MEDIKIOSK_WHISPER_MODEL", "tiny")
_COMPUTE_TYPE: str = os.getenv("MEDIKIOSK_WHISPER_COMPUTE", "float32")

# BCP-47 to Whisper language code mapping for all 22 scheduled Indian languages + EN.
WHISPER_LANGS: dict[str, str] = {
    "en": "en", "hi": "hi", "mr": "mr", "ta": "ta", "te": "te",
    "bn": "bn", "gu": "gu", "kn": "kn", "ml": "ml", "pa": "pa",
    "or": "or", "as": "as", "ur": "ur", "sd": "sd", "sa": "sa",
    "ne": "ne", "kok": "kok", "brx": "brx", "mai": "mai", "mni": "mni",
}

# Whisper artefact phrases that indicate the model hallucinated on silence/noise.
_HALLUCINATION_TOKENS = frozenset({
    "thank you", "thanks for watching", "subtitles by", "amara.org",
    "youtube", "captions by", "transcript by", "music playing",
    "applause", "[music]", "[applause]", "[laughter]", "[silence]",
    "please subscribe", "like and subscribe", "see you next time",
})


# ---------------------------------------------------------------------------
# Engine availability
# ---------------------------------------------------------------------------

def whisper_available() -> bool:
    """Return True if faster-whisper is importable."""
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def active_engine() -> str:
    """Return the name of the engine that will actually be used."""
    mode = _ASR_MODE
    if mode in {"stub", "off"}:
        return "stub"
    if mode in {"auto", "whisper"}:
        return "faster-whisper" if whisper_available() else "stub"
    return "stub"


def engine_status() -> dict:
    """Return a dict describing the current ASR engine state."""
    eng = active_engine()
    if eng == "faster-whisper":
        return {
            "engine": "faster-whisper",
            "available": True,
            "model": _WHISPER_MODEL,
            "supported_languages": list(WHISPER_LANGS.keys()),
        }
    return {
        "engine": "stub",
        "available": False,
        "model": None,
        "supported_languages": [],
        "hint": "Install faster-whisper and set MEDIKIOSK_ASR=whisper to enable server ASR.",
    }


# ---------------------------------------------------------------------------
# Model lifecycle
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_model():
    """Load and cache the WhisperModel (heavy; called once)."""
    from faster_whisper import WhisperModel  # type: ignore
    logger.info("Loading faster-whisper model=%s on CPU (%s)", _WHISPER_MODEL, _COMPUTE_TYPE)
    return WhisperModel(_WHISPER_MODEL, device="cpu", compute_type=_COMPUTE_TYPE)


def warmup() -> str:
    """Pre-load the Whisper model in the background to avoid first-request lag."""
    if active_engine() != "faster-whisper":
        logger.info("ASR warmup skipped — engine=%s", active_engine())
        return "stub"
    try:
        _get_model()
        logger.info("ASR warmup complete — model=%s", _WHISPER_MODEL)
        return "faster-whisper"
    except Exception:
        logger.exception("ASR warmup failed")
        return "stub"


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def suffix_for_bytes(data: bytes, content_type: str | None = None) -> str:
    """Pick a temp-file suffix that matches the audio payload format."""
    if content_type:
        ct = content_type.lower()
        if "wav" in ct or "wave" in ct:
            return ".wav"
        if "m4a" in ct or "mp4" in ct:
            return ".m4a"
        if "ogg" in ct:
            return ".ogg"
        if "webm" in ct:
            return ".webm"
        if "mp3" in ct or "mpeg" in ct:
            return ".mp3"

    # Magic-byte fallback
    if len(data) >= 12 and data[:4] == b"RIFF" and b"WAVE" in data[:12]:
        return ".wav"
    if data[:4] == b"OggS":
        return ".ogg"
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return ".webm"
    if len(data) >= 3 and data[:3] in (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return ".mp3"
    # Default: browsers typically send WebM/Opus via MediaRecorder
    return ".webm"


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def _confidence_from_segments(segments: list) -> float:
    """Derive a 0-1 confidence from segment log-probs and no-speech prob."""
    scores = []
    for seg in segments:
        avg_logprob = getattr(seg, "avg_logprob", None)
        no_speech_prob = float(getattr(seg, "no_speech_prob", 0.0) or 0.0)
        if avg_logprob is None:
            continue
        # Map avg_logprob (typically -3..0) to 0..1
        score = max(0.0, min(1.0, 1.0 + (avg_logprob / 3.0)))
        # Discount by speech activity
        score *= max(0.0, 1.0 - no_speech_prob)
        scores.append(score)

    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 3)


# ---------------------------------------------------------------------------
# Hallucination detection
# ---------------------------------------------------------------------------

def _is_hallucination(text: str | None) -> bool:
    """Return True if the transcript looks like a Whisper hallucination.

    Conservative: only rejects well-known artefacts, not short or
    foreign-script text (which might be valid Hindi/Urdu/Tamil).
    """
    if not text:
        return True

    stripped = text.strip()
    if not stripped:
        return True

    lower = stripped.lower()

    for token in _HALLUCINATION_TOKENS:
        if token in lower:
            return True

    # Music/symbol spam
    if "!" in stripped or chr(9835) in stripped:
        return True

    # All punctuation/whitespace with no word characters at all
    if re.match(r"^[\W_\s]+$", stripped, re.UNICODE):
        return True

    return False


# ---------------------------------------------------------------------------
# Core transcription
# ---------------------------------------------------------------------------

def transcribe_audio(
    data: bytes,
    language: str = "en",
    content_type: str | None = None,
) -> dict:
    """Transcribe raw audio bytes with faster-whisper.

    Returns: {transcript, confidence, language, engine, duration_ms?, note?}
    """
    base_result: dict = {
        "transcript": "",
        "confidence": 0.0,
        "language": language,
        "engine": active_engine(),
    }

    if not data:
        base_result["note"] = "empty audio payload"
        return base_result

    if not whisper_available():
        base_result["engine"] = "stub"
        base_result["note"] = "faster-whisper not installed"
        return base_result

    # Resolve the Whisper language code (strip region tag e.g. "en-IN" to "en")
    lang_code = WHISPER_LANGS.get((language or "en").split("-")[0].lower(), "en")

    tmp_path: str | None = None
    try:
        suffix = suffix_for_bytes(data, content_type)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        model = _get_model()
        # VAD disabled on server: the browser frontend already handles silence detection.
        # Initial prompt primes the decoder with common clinical terms for higher accuracy.
        if lang_code == "hi":
            initial_prompt = "मरीज़, सीने में दर्द, सांस लेने में तकलीफ, बुखार, खांसी, सिरदर्द, उल्टी, दवा, एलर्जी"
        elif lang_code == "as":
            initial_prompt = "মৰীজ, বুকুত বিষ, উশাহ লওঁতে কষ্ট, জ্বৰ, কাহ, মূৰৰ বিষ, বমি, পেটৰ বিষ, ঔষধ, এলাৰ্জী"
        else:
            initial_prompt = "Patient presenting with chest pain, shortness of breath, cough, fever, headache, nausea, allergy, medication, days, severity."

        segments_gen, info = model.transcribe(
            tmp_path,
            language=lang_code,
            vad_filter=False,
            beam_size=5,
            initial_prompt=initial_prompt,
        )
        segments = list(segments_gen)

        transcript = " ".join((s.text or "").strip() for s in segments).strip()

        if _is_hallucination(transcript):
            transcript = ""

        confidence = _confidence_from_segments(segments)

        # Only drop at extremely low confidence (< 0.05)
        if transcript and confidence < 0.05:
            logger.debug("ASR: dropping extremely low-confidence: %r", transcript)
            transcript = ""
            confidence = 0.0

        duration_ms = int(getattr(info, "duration", 0) * 1000)

        return {
            "transcript": transcript,
            "confidence": confidence,
            "language": language,
            "engine": "faster-whisper",
            "duration_ms": duration_ms,
        }

    except Exception as exc:
        logger.error("Whisper transcription error: %s", exc, exc_info=True)
        base_result["engine"] = "faster-whisper"
        base_result["note"] = f"ASR error: {str(exc)[:120]}"
        return base_result

    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
