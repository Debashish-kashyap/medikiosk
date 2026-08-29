"""Deterministic dialogue state machine — decides WHAT to ask next.

This is the controlled clinical workflow. It traverses clinical_ontology.json based
on the patient's answers; the LLM is called only to map speech onto option values.
Branch logic lives in the ontology ('next' per option or per node), never in the LLM.

Flow per answer:
  raw touch value?  -> accept (confidence 1.0)
  spoken text?      -> llm_mapper.interpret -> value + confidence
  confidence low & unconfirmed -> ask to repeat/tap (do NOT store)
  else store -> evaluate red flags -> advance to next node

Owned by the Backend Lead lane.
"""
from __future__ import annotations

from typing import Any

from . import llm_mapper, red_flags, validation
from .ontology_loader import Ontology, load_ontology


def render_question(node: dict, lang: str, ont: Ontology) -> dict:
    """Shape a node into the payload the kiosk renders (voice + touch)."""
    payload: dict[str, Any] = {
        "node_id": node["id"],
        "field": node["field"],
        "section": node.get("section"),
        "type": node["type"],
        "allow_voice": node.get("allow_voice", True),
        "prompt": ont.localize(node["prompt"], lang),
        "help": ont.localize(node["help"], lang) if node.get("help") else None,
    }
    if node["type"] == "scale":
        payload["scale_min"] = node.get("scale_min", 0)
        payload["scale_max"] = node.get("scale_max", 10)
    else:
        payload["options"] = [
            {
                "value": opt["value"],
                "label": ont.localize(opt["label"], lang),
                "icon": opt.get("icon"),
            }
            for opt in node.get("options", [])
        ]
    return payload


def current_question(session: dict) -> dict | None:
    """Question for the session's current node (sets entry on first call)."""
    ont = load_ontology()
    if session["current_node"] is None:
        session["current_node"] = ont.entry
    if session["current_node"] == "END":
        return None
    node = ont.get_node(session["current_node"])
    return render_question(node, session["language"], ont) if node else None


def _next_node_id(node: dict, value: Any) -> str:
    """Resolve branch: option-level 'next' beats node-level 'next'. 'END' finishes."""
    if not isinstance(value, list):
        for opt in node.get("options", []):
            if opt["value"] == value and opt.get("next"):
                return opt["next"]
    return node.get("next", "END")


def process_answer(
    session: dict,
    node_id: str,
    touch_value: Any = None,
    text: str | None = None,
    confidence: float | None = None,
    confirmed: bool = False,
) -> dict:
    """Validate + store an answer and advance the machine. Returns a result dict."""
    ont = load_ontology()
    node = ont.get_node(node_id)
    if node is None:
        return {"status": "error", "message": f"Unknown question '{node_id}'."}

    lang = session["language"]

    # --- Resolve the value + provenance ------------------------------------
    if touch_value is not None:
        value, conf, source = touch_value, 1.0, "touch"
        method = "touch"
    elif text is not None:
        interp = llm_mapper.interpret(node, text, lang)
        value, conf, method = interp["value"], interp["confidence"], interp["method"]
        if confidence is not None:
            conf = min(conf, confidence)
        source = "voice"
    else:
        return {"status": "error", "message": "No answer provided."}

    # --- Confidence gate (noisy-room / ASR safety) -------------------------
    if value is None or validation.needs_confirmation(source, conf, confirmed):
        return {
            "status": "needs_confirmation",
            "node_id": node_id,
            "interpreted_value": value,
            "interpreted_label": _label_for(node, value, lang, ont),
            "confidence": round(conf, 2),
            "message": _confirm_message(lang),
            "question": render_question(node, lang, ont),
        }

    # --- Store (validated) --------------------------------------------------
    session["answers"][node["field"]] = value
    session["answer_meta"][node["field"]] = {
        "source": source,
        "confidence": round(conf, 2),
        "method": method,
        "transcript": text,
    }
    session["current_node"] = node_id  # normalise

    # --- Red-flag safety layer (rules, not LLM) -----------------------------
    prev_ids = {f["id"] for f in session["red_flags"]}
    fired = red_flags.evaluate(session["answers"], ont.red_flags, lang)
    session["red_flags"] = fired
    newly_fired = [f for f in fired if f["id"] not in prev_ids]

    # --- Advance ------------------------------------------------------------
    nxt = _next_node_id(node, value)
    done = nxt == "END" or nxt is None
    session["current_node"] = "END" if done else nxt
    if done:
        session["status"] = "complete"

    next_q = None if done else render_question(ont.get_node(nxt), lang, ont)
    return {
        "status": "accepted",
        "stored": {"field": node["field"], "value": value},
        "red_flags_new": newly_fired,
        "red_flags_all": fired,
        "done": done,
        "summary_ready": done,
        "next_question": next_q,
    }


def _label_for(node: dict, value: Any, lang: str, ont: Ontology) -> str | None:
    if value is None:
        return None
    for opt in node.get("options", []):
        if opt["value"] == value:
            return ont.localize(opt["label"], lang)
    return str(value)


def _confirm_message(lang: str) -> str:
    return {
        "en": "I didn't catch that clearly. Please say it again, or tap an option below.",
        "hi": "मुझे ठीक से समझ नहीं आया। कृपया दोबारा बोलें, या नीचे विकल्प चुनें।",
    }.get(lang, "I didn't catch that clearly. Please repeat, or tap an option.")
