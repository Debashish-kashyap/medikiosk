"""Bounded LLM interface — the LLM's ONLY jobs.

Design principle (the heart of the pitch): the LLM is NOT the source of truth.
It never decides what to ask, never diagnoses, never invents clinical facts.
Its scope is strictly:
    1. map free speech -> one of the node's predefined option values  (interpret)
    2. phrase the physician narrative from ALREADY-VERIFIED fields      (phrase_hpi)

Everything here has a deterministic offline fallback (alias/keyword matching) so the
whole system runs on a laptop with NO API key for the Day-1 demo. When MEDIKIOSK_LLM
is configured, swap in a real call inside `_llm_interpret` — keep the JSON-schema-
constrained contract so output can only ever be a known value.

Owned by the AI-NLU lane.
"""
from __future__ import annotations

import os
import re
from typing import Any

USE_LLM = os.getenv("MEDIKIOSK_LLM", "").lower() in {"1", "true", "openai", "on"}


def interpret(node: dict, text: str, lang: str = "en") -> dict:
    """Map spoken text onto a node value. Returns {value, confidence, method}.

    Low confidence (< validation threshold) makes the kiosk ask to repeat/tap.
    """
    text_norm = (text or "").strip().lower()
    if not text_norm:
        return {"value": None, "confidence": 0.0, "method": "empty"}

    # Scale nodes: pull the first integer in range.
    if node.get("type") == "scale":
        return _interpret_scale(node, text_norm)

    # Try deterministic alias matching first (fast, free, explainable).
    result = _interpret_aliases(node, text_norm, lang)

    # Optional real LLM only if aliases were ambiguous AND a model is configured.
    if USE_LLM and result["confidence"] < 0.6:
        try:
            return _llm_interpret(node, text, lang)
        except Exception:
            pass  # fail safe to the alias result
    return result


def _interpret_scale(node: dict, text_norm: str) -> dict:
    lo = node.get("scale_min", 0)
    hi = node.get("scale_max", 10)
    for token in re.findall(r"\d+", text_norm):
        n = int(token)
        if lo <= n <= hi:
            return {"value": n, "confidence": 0.9, "method": "scale"}
    words = {"zero": 0, "shunya": 0, "ten": 10, "das": 10, "five": 5, "paanch": 5}
    for w, n in words.items():
        if w in text_norm:
            return {"value": n, "confidence": 0.75, "method": "scale-word"}
    return {"value": None, "confidence": 0.2, "method": "scale-none"}


def _interpret_aliases(node: dict, text_norm: str, lang: str) -> dict:
    matches: list[tuple[str, float]] = []
    for opt in node.get("options", []):
        candidates = list(opt.get("aliases", []))
        for l in (opt.get("label") or {}).values():
            candidates.append(l)
        for cand in candidates:
            c = str(cand).strip().lower()
            if not c:
                continue
            if c == text_norm:
                matches.append((opt["value"], 0.97))
            elif c in text_norm or text_norm in c:
                matches.append((opt["value"], 0.82))

    if not matches:
        return {"value": None, "confidence": 0.3, "method": "alias-none"}

    # Highest-confidence match wins; if several distinct values tie, mark ambiguous.
    matches.sort(key=lambda m: m[1], reverse=True)
    best_value, best_conf = matches[0]
    distinct = {m[0] for m in matches}
    if len(distinct) > 1:
        best_conf = min(best_conf, 0.55)   # ambiguous -> likely confirm
    return {"value": best_value, "confidence": best_conf, "method": "alias"}


def _llm_interpret(node: dict, text: str, lang: str) -> dict:
    """TODO (AI-NLU lane): real, schema-constrained model call.

    Contract to preserve:
      - system prompt: "Map the patient's words to EXACTLY ONE of these values: [...].
        If none fit, return null. Do not invent values."
      - use function-calling / JSON schema whose enum == the node option values
      - return {"value": <enum|null>, "confidence": <0..1>, "method": "llm"}
    Wire Bhashini/AI4Bharat translation before this step for regional languages.
    """
    raise NotImplementedError("Configure a schema-constrained LLM call here.")


def phrase_hpi(narrative_fields: dict[str, Any], lang: str = "en") -> str:
    """Phrase the History of Present Illness from verified fields.

    Offline: deterministic template (below). With an LLM configured, replace with a
    call that is given ONLY these verified fields and told to write 1-2 neutral
    clinical sentences — no new facts, no diagnosis.
    """
    if USE_LLM:
        try:
            return _llm_phrase(narrative_fields, lang)
        except Exception:
            pass
    return _template_hpi(narrative_fields)


def _template_hpi(f: dict[str, Any]) -> str:
    cc = f.get("chief_complaint")
    if cc == "chest_pain":
        parts = ["Patient reports chest pain"]
        if f.get("cp_site"):
            parts.append(f"located {f['cp_site'].replace('_', ' ')}")
        if f.get("cp_character"):
            parts.append(f"{f['cp_character']} in character")
        if f.get("cp_onset"):
            parts.append(f"onset {f['cp_onset'].replace('_', ' ')}")
        if f.get("cp_radiation") and f["cp_radiation"] != "no":
            parts.append(f"radiating to {f['cp_radiation'].replace('_', ' ')}")
        assoc = []
        if f.get("cp_breathless") == "yes":
            assoc.append("breathlessness")
        if f.get("cp_sweating") == "yes":
            assoc.append("sweating")
        if assoc:
            parts.append("associated with " + " and ".join(assoc))
        if f.get("cp_severity") is not None:
            parts.append(f"severity {f['cp_severity']}/10")
        return ", ".join(parts) + "."
    if cc == "fever":
        parts = ["Patient reports fever"]
        if f.get("fever_onset"):
            parts.append(f"onset {f['fever_onset'].replace('_', ' ')}")
        if f.get("fever_grade"):
            parts.append(f"{f['fever_grade'].replace('_', ' ')}")
        assoc = f.get("fever_assoc")
        if isinstance(assoc, list) and assoc and "none" not in assoc:
            parts.append("with " + ", ".join(a.replace("_", " ") for a in assoc))
        return ", ".join(parts) + "."
    return "Patient presents with the above chief complaint (see structured fields)."


def _llm_phrase(fields: dict[str, Any], lang: str) -> str:
    raise NotImplementedError("Configure a summary LLM call here.")
