"""Module C — structured, physician-ready summary from VERIFIED fields only.

Synthesizes the dialogue answers (+ any digitized documents from Module B) into a
standard clinical layout: Chief complaint -> HPI -> Past -> Drug/Allergy -> ROS ->
Prior investigations. The narrative prose comes from llm_mapper.phrase_hpi, which only
rephrases confirmed fields. The physician edits/confirms this on their screen — it is
always a draft, never an autonomous diagnosis.

Owned by the AI-NLU lane + Physician-UI lane.
"""
from __future__ import annotations

from typing import Any

from . import llm_mapper, validation
from .ontology_loader import Ontology, load_ontology


def build_summary(session: dict) -> dict:
    ont = load_ontology()
    lang = session["language"]
    answers = session["answers"]

    def label(node_id: str, value: Any) -> Any:
        if isinstance(value, list):
            return [_opt_label(ont, node_id, v, lang) for v in value]
        return _opt_label(ont, node_id, value, lang)

    chief = label("chief_complaint", answers.get("chief_complaint"))

    past = answers.get("past_history")
    past_labels = label("past_history", past) if past else []
    if isinstance(past_labels, list) and (not past_labels or "none" in (past or [])):
        past_display = "No known chronic conditions reported."
    else:
        past_display = ", ".join(past_labels) if isinstance(past_labels, list) else str(past_labels)

    drug = answers.get("drug_allergy")
    drug_display = {
        "yes": "Patient reports a drug allergy — CONFIRM specifics.",
        "no": "No known drug allergy reported.",
    }.get(drug, "Not asked.")

    summary = {
        "chief_complaint": chief or "Not captured",
        "hpi": llm_mapper.phrase_hpi(answers, lang),
        "past_medical": past_display,
        "drug_allergy": drug_display,
        "review_of_systems": _ros(answers),
        "prior_investigations": _documents_summary(session),
        "red_flags": session.get("red_flags", []),
        "contradictions": validation.detect_contradictions(answers),
        "raw_fields": answers,               # for the physician "show details" view
        "language": lang,
        "disclaimer": (
            "Draft generated from patient self-report and uploaded documents. "
            "For physician review, editing and confirmation. Not a diagnosis."
        ),
    }
    return summary


def _ros(answers: dict) -> str:
    findings = []
    if answers.get("cp_breathless") == "yes":
        findings.append("breathlessness")
    if answers.get("cp_sweating") == "yes":
        findings.append("diaphoresis")
    assoc = answers.get("fever_assoc")
    if isinstance(assoc, list):
        findings += [a.replace("_", " ") for a in assoc if a != "none"]
    return "Positive for: " + ", ".join(findings) + "." if findings else "Unremarkable / not elicited."


def _documents_summary(session: dict) -> list[dict]:
    """Chronologically ordered digitized documents (Module B output)."""
    docs = session.get("documents", [])
    return sorted(docs, key=lambda d: d.get("date") or "", reverse=True)


def _opt_label(ont: Ontology, node_id: str, value: Any, lang: str) -> Any:
    opt = ont.option(node_id, value) if isinstance(value, str) else None
    if opt:
        return ont.localize(opt["label"], lang)
    return value
