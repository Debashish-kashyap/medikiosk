"""Validation & confidence layer.

Two jobs:
1. Decide when an ASR (voice) answer is too uncertain and must be confirmed / re-tapped.
   This is the answer to "how accurate is your speech recognition?" and "noisy hospital".
2. Basic contradiction detection, surfaced to the physician (never auto-resolved).

Owned by the Backend Lead lane.
"""
from __future__ import annotations

from typing import Any

# Below this ASR/mapping confidence we do NOT accept a spoken answer silently;
# the kiosk asks the patient to repeat or tap an option.
CONFIDENCE_THRESHOLD = 0.6


def needs_confirmation(source: str, confidence: float, confirmed: bool) -> bool:
    if confirmed:
        return False
    if source != "voice":
        return False
    return confidence < CONFIDENCE_THRESHOLD


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
