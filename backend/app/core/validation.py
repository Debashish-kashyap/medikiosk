"""Validation & confidence layer.

Two jobs:
1. Decide when an ASR (voice) answer is too uncertain and must be confirmed / re-tapped.
   This is the answer to "how accurate is your speech recognition?" and "noisy hospital".
2. Basic contradiction detection, surfaced to the physician (never auto-resolved).

Owned by the Backend Lead lane.
Updated by Lane 4 — engine-aware confidence thresholds (T2).
"""
from __future__ import annotations

from typing import Any

CONFIDENCE_THRESHOLD_DEFAULT = 0.50
CONFIDENCE_THRESHOLD_WHISPER = 0.50
CONFIDENCE_THRESHOLD_WEBSPEECH = 0.50

def _threshold_for_engine(engine: str | None = None) -> float:
    """Return the appropriate confidence threshold for the given ASR engine."""
    if engine in {"faster-whisper", "whisper"}:
        return CONFIDENCE_THRESHOLD_WHISPER
    if engine in {"webspeech", "web-speech"}:
        return CONFIDENCE_THRESHOLD_WEBSPEECH
    if engine == "mock":
        return 0.0
    return CONFIDENCE_THRESHOLD_DEFAULT

def needs_confirmation(
    source: str,
    confidence: float,
    confirmed: bool,
    engine: str | None = None,
) -> bool:
    """Return True if the answer is too uncertain to accept silently."""
    if confirmed:
        return False
    if source != "voice":
        return False
    return confidence < _threshold_for_engine(engine)

def detect_contradictions(answers: dict[str, Any]) -> list[str]:
    """Cheap, illustrative contradiction checks. Extend per complaint.

    Returns human-readable notes for the physician summary — we flag, never fix.
    """
    notes: list[str] = []

    past = answers.get("past_history")
    if isinstance(past, list) and "none" in past and len(past) > 1:
        notes.append(
            "Patient selected 'no known conditions' together with specific conditions "
            "— please verify past history."
        )

    return notes
