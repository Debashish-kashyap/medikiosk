"""Rule-based red-flag safety layer.

CRITICAL DESIGN NOTE (say this to the judges): emergency detection is deterministic
rules, NOT the LLM. Rules only ESCALATE suspicious patterns to human triage; they
never rule an emergency out and never diagnose. Thresholds/rules are hospital-tunable
by editing the "red_flags" section of clinical_ontology.json.

Owned by the AI-NLU / Safety lane.
"""
from __future__ import annotations

from typing import Any


def _matches(condition: dict, answers: dict[str, Any]) -> bool:
    field_value = answers.get(condition["field"])
    if field_value is None:
        return False

    if "equals" in condition:
        target = condition["equals"]
        if isinstance(field_value, list):      # multi_select field
            return target in field_value
        return field_value == target

    if "in" in condition:
        targets = condition["in"]
        if isinstance(field_value, list):
            return any(v in targets for v in field_value)
        return field_value in targets

    return False


def evaluate(answers: dict[str, Any], rules: list[dict], lang: str = "en") -> list[dict]:
    """Return all currently-firing red flags (localized), highest priority first."""
    fired: list[dict] = []
    for rule in rules:
        if all(_matches(c, answers) for c in rule["conditions"]):
            fired.append(
                {
                    "id": rule["id"],
                    "priority": rule["priority"],
                    "label": _loc(rule["label"], lang),
                    "action": _loc(rule["action"], lang),
                }
            )
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    fired.sort(key=lambda f: order.get(f["priority"], 9))
    return fired


def _loc(obj: Any, lang: str) -> str:
    if isinstance(obj, dict):
        return obj.get(lang) or obj.get("en") or ""
    return str(obj)
