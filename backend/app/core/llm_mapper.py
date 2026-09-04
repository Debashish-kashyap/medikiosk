"""Bounded LLM & Semantic Mapper — the LLM's ONLY jobs.

Design principle: the LLM is NOT the source of truth.
It never decides what to ask, never diagnoses, never invents clinical facts.
Its scope is strictly:
    1. map free speech -> one of the node's predefined option values  (interpret)
    2. phrase the physician narrative from ALREADY-VERIFIED fields      (phrase_hpi)

Equipped with smart clinical alias matching, negation handling (e.g. "no breathlessness" -> no),
multi-select extraction, scale word parsing, and fuzzy phonetic matching.
"""
from __future__ import annotations

import difflib
import json
import logging
import os
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

# Circuit breaker: if Gemini experiences 503 high demand or network timeouts,
# pause remote calls for 60 seconds to guarantee instant, freeze-free kiosk operation.
_GEMINI_CIRCUIT_OPEN_UNTIL = 0.0

USE_LLM = os.getenv("MEDIKIOSK_LLM", "").lower() in {"1", "true", "openai", "on"}

# Common negation terms in English, Hindi & Assamese
NEGATION_WORDS = {
    "no", "not", "none", "nothing", "never", "nah", "nope", "without",
    "nahi", "nahin", "na", "koi nahi", "kuch nahi", "bilkul nahi", "mat",
    "nohoi", "nahai", "nai", "eku nai", "kono nai", "নহয়", "নাই", "একো নাই",
}

AFFIRMATION_WORDS = {
    "yes", "yeah", "yep", "sure", "definitely", "present", "a lot", "severe", "much",
    "haan", "ha", "bilkul", "bohot", "bahut", "zyada", "hai",
    "hoi", "haya", "ase", "bohut", "হয়", "আছে", "বহুত",
}


def interpret(node: dict, text: str, lang: str = "en") -> dict:
    """Map spoken text onto a node value. Returns {value, confidence, method}."""
    text_norm = (text or "").strip().lower()
    if not text_norm:
        return {"value": None, "confidence": 0.0, "method": "empty"}

    # 1. Scale nodes (0 - 10)
    if node.get("type") == "scale":
        return _interpret_scale(node, text_norm)

    # 2. Yes/No nodes (with intelligent negation handling)
    if node.get("type") == "yes_no":
        return _interpret_yes_no(node, text_norm, lang)

    # 3. Free text nodes (direct voice/text capture + quick option matching)
    if node.get("type") == "free_text":
        quick_opts = node.get("quick_options", [])
        for opt in quick_opts:
            val = opt.get("value", "")
            lbl = opt.get("label", {})
            opt_texts = [val.lower(), val.replace("_", " ").lower()]
            if isinstance(lbl, dict):
                opt_texts.extend([str(v).lower() for v in lbl.values()])
            if any(ot in text_norm for ot in opt_texts if ot):
                return {"value": val, "confidence": 1.0, "method": "quick_option"}
        return {"value": text.strip(), "confidence": 0.95, "method": "free_text"}

    # 4. Multi-select and Single-select matching
    result = _interpret_aliases(node, text_norm, lang)

    # Optional real LLM only if aliases were ambiguous AND a model is configured AND circuit is healthy.
    if USE_LLM and result["confidence"] < 0.55:
        if time.time() >= _GEMINI_CIRCUIT_OPEN_UNTIL:
            try:
                return _llm_interpret(node, text, lang)
            except Exception:
                pass

    return result


SCALE_WORDS = {
    # English
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    # Hindi (Latin & Devanagari)
    "shunya": 0, "ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4,
    "paanch": 5, "panch": 5, "chhe": 6, "che": 6, "saat": 7, "sat": 7,
    "aath": 8, "ath": 8, "nau": 9, "das": 10, "duss": 10,
    "शून्य": 0, "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "पांच": 5,
    "छह": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
    # Assamese (Latin & Eastern Nagari / Bengali-Assamese script)
    "xunya": 0, "dui": 2, "tini": 3, "sari": 4, "paas": 5, "soy": 6, "xaat": 7, "naw": 9, "doh": 10,
    "শূণ্য": 0, "দুই": 2, "তিনি": 3, "চাৰি": 4, "পাঁচ": 5, "ছয়": 6, "সাত": 7, "আঠ": 8, "ন": 9, "দহ": 10,
}


def _interpret_scale(node: dict, text_norm: str) -> dict:
    lo = node.get("scale_min", 0)
    hi = node.get("scale_max", 10)

    # Direct digit match
    for token in re.findall(r"\d+", text_norm):
        n = int(token)
        if lo <= n <= hi:
            return {"value": n, "confidence": 0.95, "method": "scale-digit"}

    # Word numbers (e.g. "seven", "saat", "eight", "aath")
    for w, n in SCALE_WORDS.items():
        if _match_candidate(w, text_norm) > 0.0:
            if lo <= n <= hi:
                return {"value": n, "confidence": 0.88, "method": "scale-word"}

    # Relative severity terms
    if any(w in text_norm for w in ["mild", "halka", "thoda", "kam", "bearable"]):
        return {"value": 3, "confidence": 0.75, "method": "scale-estimate"}
    if any(w in text_norm for w in ["moderate", "medium", "theek theek", "average"]):
        return {"value": 5, "confidence": 0.75, "method": "scale-estimate"}
    if any(w in text_norm for w in ["severe", "very bad", "bohot zyada", "tez", "unbearable", "bahut", "extreme", "maximum"]):
        return {"value": 9, "confidence": 0.85, "method": "scale-estimate"}

    return {"value": None, "confidence": 0.2, "method": "scale-none"}


def _interpret_yes_no(node: dict, text_norm: str, lang: str) -> dict:
    """Intelligently map yes/no taking into account explicit negations (e.g. 'no sweat')."""
    words = [w for w in re.split(r"\W+", text_norm) if w]

    has_neg = any(w in NEGATION_WORDS for w in words) or any(phrase in text_norm for phrase in ["koi nahi", "kuch nahi", "bilkul nahi", "no ", "not "])
    has_aff = any(w in AFFIRMATION_WORDS for w in words) or any(phrase in text_norm for phrase in ["yes", "haan", "ha", "a lot", "very much"])

    # If explicit negative words are present (e.g. "no breathlessness", "nahi hai", "not at all")
    if has_neg and not has_aff:
        return {"value": "no", "confidence": 0.95, "method": "yes_no-negation"}

    # If explicit affirmative words are present (e.g. "yes", "haan", "a lot")
    if has_aff and not has_neg:
        return {"value": "yes", "confidence": 0.95, "method": "yes_no-affirmation"}

    # Otherwise fall back to alias candidate matching
    return _interpret_aliases(node, text_norm, lang)


def _match_candidate(cand: str, text: str) -> float:
    c = cand.strip().lower()
    t = text.strip().lower()
    if not c or not t:
        return 0.0

    if c == t:
        return 0.98

    escaped = re.escape(c)
    pattern = rf"(?:^|\W){escaped}(?:$|\W)"
    if re.search(pattern, t):
        return 0.92 if len(c) > 2 else 0.82

    if c in t:
        ratio = len(c) / len(t)
        return max(0.82, 0.72 + 0.25 * ratio)

    if t in c:
        ratio = len(t) / len(c)
        if ratio >= 0.50:
            return max(0.80, 0.68 + 0.30 * ratio)
        elif ratio >= 0.30 and len(t) >= 3:
            return 0.65

    c_words = [w for w in re.split(r"\W+", c) if len(w) > 1]
    t_words = [w for w in re.split(r"\W+", t) if len(w) > 1]
    if c_words and t_words:
        common_words = set(c_words) & set(t_words)
        if common_words:
            overlap = len(common_words) / min(len(c_words), len(t_words))
            if overlap >= 0.50:
                return 0.88

    sim = difflib.SequenceMatcher(None, c, t).ratio()
    if sim >= 0.70:
        return round(0.60 + (sim - 0.70) * 0.80, 2)

    if c_words and t_words:
        max_word_sim = max(difflib.SequenceMatcher(None, cw, tw).ratio() for cw in c_words for tw in t_words)
        if max_word_sim >= 0.75:
            return round(0.60 + (max_word_sim - 0.75) * 0.80, 2)

    # NEW: phonetic fallback — catches pronunciation-driven ASR errors that
    # look nothing alike in spelling ("thane belt" vs "thin build") but
    # sound close. Uses Double Metaphone; falls back cleanly if unavailable.
    phon_score = _phonetic_match(c, t)
    if phon_score > 0:
        return phon_score

    return 0.0


def _phonetic_match(cand: str, text: str) -> float:
    """Compare candidate and text by phonetic code, word-by-word."""
    try:
        from metaphone import doublemetaphone  # type: ignore
    except ImportError:
        return 0.0  # graceful no-op if the package isn't installed

    c_words = [w for w in re.split(r"\W+", cand) if w]
    t_words = [w for w in re.split(r"\W+", text) if w]
    if not c_words or not t_words:
        return 0.0

    best = 0.0
    for cw in c_words:
        c_codes = doublemetaphone(cw)
        for tw in t_words:
            t_codes = doublemetaphone(tw)
            # Any overlap between primary/secondary metaphone codes = phonetic match
            if any(cc and cc == tc for cc in c_codes for tc in t_codes):
                # Weight by how much of the word matched, so "thin"↔"thane"
                # (short, common word) scores lower than a longer distinctive match.
                weight = min(len(cw), len(tw)) / max(len(cw), len(tw))
                best = max(best, 0.55 + 0.20 * weight)
    return round(best, 2) if best >= 0.55 else 0.0


def _interpret_aliases(node: dict, text_norm: str, lang: str) -> dict:
    is_multi = node.get("type") == "multi_select"

    # Multi-select general negative check (e.g. "no past history", "healthy", "kuch nahi")
    if is_multi:
        if any(neg in text_norm for neg in ["none", "nothing", "no past", "no disease", "no condition", "healthy", "fit", "kuch nahi", "koi nahi", "koi bimari nahi"]):
            return {"value": ["none"], "confidence": 0.95, "method": "multi-negation"}

    matched_options: list[tuple[str, float]] = []

    for opt in node.get("options", []):
        candidates = list(opt.get("aliases", []))
        for l in (opt.get("label") or {}).values():
            candidates.append(l)

        best_opt_conf = 0.0
        for cand in candidates:
            conf = _match_candidate(str(cand), text_norm)
            if conf > best_opt_conf:
                best_opt_conf = conf

        if best_opt_conf >= 0.50:  # Accept >= 50% confidence match
            matched_options.append((opt["value"], best_opt_conf))

    if not matched_options:
        return {"value": None, "confidence": 0.3, "method": "alias-none"}

    # Multi-select case
    if is_multi:
        values = list(dict.fromkeys(v for v, _ in matched_options))
        # If 'none' was selected along with specific conditions, remove 'none'
        if len(values) > 1 and "none" in values:
            values = [v for v in values if v != "none"]
        avg_conf = sum(c for _, c in matched_options) / len(matched_options)
        return {"value": values, "confidence": round(avg_conf, 2), "method": "alias-multi"}

    # Single select: highest confidence match wins
    matched_options.sort(key=lambda m: m[1], reverse=True)
    best_value, best_conf = matched_options[0]
    distinct = {m[0] for m in matched_options if m[1] >= best_conf - 0.05}
    if len(distinct) > 1:
        best_conf = min(best_conf, 0.55)  # ambiguous -> prompt confirmation

    return {"value": best_value, "confidence": best_conf, "method": "alias"}


def _call_gemini_text(prompt: str, temperature: float = 0.2) -> str:
    """Call Google AI Studio Gemini API with strict 2.0s timeout and automatic 60s circuit breaker."""
    global _GEMINI_CIRCUIT_OPEN_UNTIL

    now = time.time()
    if now < _GEMINI_CIRCUIT_OPEN_UNTIL:
        raise RuntimeError("Gemini circuit breaker open (remote call bypassed to prevent freeze)")

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured")

    model = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

    import httpx
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }

    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code in (503, 429):
                _GEMINI_CIRCUIT_OPEN_UNTIL = time.time() + 60.0
                logger.warning("Gemini %s (demand spike). 60s circuit breaker enabled; using instant local fallback.", resp.status_code)
                raise RuntimeError(f"Gemini {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("No candidate in Gemini response")
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise RuntimeError("Empty response parts from Gemini")
        return parts[0].get("text", "").strip()

    except Exception as e:
        _GEMINI_CIRCUIT_OPEN_UNTIL = time.time() + 45.0
        logger.warning("Gemini fast-timeout/error (%s). Instant clinical fallback activated.", e)
        raise


def _llm_interpret(node: dict, text: str, lang: str) -> dict:
    """Schema-constrained Gemini LLM fallback for ambiguous responses."""
    import json
    options_summary = [
        {"value": opt["value"], "aliases": opt.get("aliases", []), "labels": opt.get("label", {})}
        for opt in node.get("options", [])
    ]
    prompt = (
        f"You are a clinical semantic matcher for a medical triage kiosk.\n"
        f"Match the patient's spoken text to exactly ONE valid option value.\n"
        f"Node Type: {node.get('type')}\n"
        f"Allowed Options: {json.dumps(options_summary)}\n"
        f"Patient input: \"{text}\"\n"
        f"Language: {lang}\n"
        f"Respond ONLY with a JSON object in this exact format: {{\"value\": \"<selected_value>\", \"confidence\": 0.95}}"
    )
    try:
        raw = _call_gemini_text(prompt, temperature=0.0)
        clean = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean).strip()
        parsed = json.loads(clean)
        val = parsed.get("value")
        conf = float(parsed.get("confidence", 0.8))
        # Validate that the selected value is legal for this node
        legal_values = {opt["value"] for opt in node.get("options", [])}
        if val in legal_values:
            return {"value": val, "confidence": conf, "method": "gemini-llm"}
    except Exception:
        pass

    return {"value": None, "confidence": 0.3, "method": "llm-failed"}


def phrase_hpi(
    narrative_fields: dict[str, Any],
    lang: str = "en",
    answer_meta: dict[str, Any] | None = None,
) -> str:
    """Phrase the History of Present Illness from verified fields and voice transcripts."""
    if (USE_LLM or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")) and time.time() >= _GEMINI_CIRCUIT_OPEN_UNTIL:
        try:
            return _llm_phrase(narrative_fields, lang, answer_meta)
        except Exception:
            pass
    return _template_hpi(narrative_fields, answer_meta)


def _template_hpi(f: dict[str, Any], answer_meta: dict[str, Any] | None = None) -> str:
    """Construct a detailed clinical HPI paragraph from structured fields and voice transcripts."""
    cc = f.get("chief_complaint")
    sentences = []

    # 1. Primary complaint narrative
    if cc == "chest_pain":
        parts = ["Patient presents with chest pain"]
        if f.get("cp_site"):
            parts.append(f"located in the {f['cp_site'].replace('_', ' ')}")
        if f.get("cp_character"):
            parts.append(f"described as {f['cp_character'].replace('_', ' ')}")
        if f.get("cp_onset"):
            onset_str = {
                "under_1h": "started less than 1 hour ago",
                "today": "started earlier today",
                "few_days": "present for a few days",
                "over_week": "present for more than a week",
            }.get(f["cp_onset"], f"onset {f['cp_onset'].replace('_', ' ')}")
            parts.append(onset_str)
        if f.get("cp_radiation") and f["cp_radiation"] != "no":
            parts.append(f"radiating to the {f['cp_radiation'].replace('_', ' ')}")
        assoc = []
        if f.get("cp_breathless") == "yes":
            assoc.append("dyspnea")
        if f.get("cp_sweating") == "yes":
            assoc.append("diaphoresis")
        if assoc:
            parts.append("associated with " + " and ".join(assoc))
        if f.get("cp_severity") is not None:
            parts.append(f"rated at {f['cp_severity']}/10 on severity scale")
        sentences.append(", ".join(parts) + ".")

    elif cc == "fever":
        parts = ["Patient presents with fever"]
        if f.get("fever_onset"):
            onset_str = {
                "under_1h": "started less than 1 hour ago",
                "today": "started earlier today",
                "few_days": "persisting for a few days",
                "over_week": "persisting for over a week",
            }.get(f["fever_onset"], f"onset {f['fever_onset'].replace('_', ' ')}")
            parts.append(onset_str)
        if f.get("fever_grade"):
            grade_str = {
                "high": "documented as high grade",
                "moderate": "documented as moderate grade",
                "mild": "documented as low grade",
                "with_chills": "associated with chills and rigors",
            }.get(f["fever_grade"], f"{f['fever_grade'].replace('_', ' ')}")
            parts.append(grade_str)
        assoc = f.get("fever_assoc")
        if isinstance(assoc, list) and assoc and "none" not in assoc:
            assoc_clean = [a.replace("_", " ") for a in assoc]
            parts.append("associated with " + ", ".join(assoc_clean))
        sentences.append(", ".join(parts) + ".")

    elif cc == "cough":
        sentences.append("Patient presents with cough and respiratory symptoms.")

    elif cc == "headache":
        sentences.append("Patient presents with acute headache / cranial discomfort.")

    elif cc == "abdominal_pain":
        sentences.append("Patient presents with abdominal discomfort and pain.")

    elif cc == "other":
        sentences.append("Patient presents with general health complaints for clinical evaluation.")

    elif cc:
        sentences.append(f"Patient presents with chief complaint of {str(cc).replace('_', ' ')}.")
    else:
        sentences.append("Patient presents for outpatient clinical evaluation.")

    # 2. Add verbatim patient voice statements if captured
    if answer_meta:
        transcripts = []
        for field, meta in answer_meta.items():
            if isinstance(meta, dict) and meta.get("transcript"):
                t = meta["transcript"].strip()
                if t and len(t) > 2 and t not in transcripts:
                    transcripts.append(t)
        if transcripts:
            combined_voice = '"; "'.join(transcripts)
            sentences.append(f'Patient reported: "{combined_voice}".')

    # 3. Past Medical History
    past = f.get("past_history")
    if past and isinstance(past, list) and "none" not in past and len(past) > 0:
        past_str = ", ".join(p.replace("_", " ") for p in past)
        sentences.append(f"Past medical history is notable for {past_str}.")
    elif past == ["none"] or (isinstance(past, list) and "none" in past):
        sentences.append("No prior chronic medical conditions reported.")

    # 4. Drug Allergies
    allergy = f.get("drug_allergy")
    if allergy == "yes":
        sentences.append("Patient reports positive drug allergy history (specific allergen verification required).")
    elif allergy == "no":
        sentences.append("No known drug allergies reported.")

    return " ".join(sentences)


def _llm_phrase(
    fields: dict[str, Any],
    lang: str,
    answer_meta: dict[str, Any] | None = None,
) -> str:
    """Generate concise, professional clinical HPI narrative using Gemini."""
    import json
    payload = {
        "verified_answers": fields,
    }
    if answer_meta:
        payload["patient_spoken_statements"] = {
            k: v.get("transcript") for k, v in answer_meta.items() if isinstance(v, dict) and v.get("transcript")
        }

    prompt = (
        f"You are a clinical documentation assistant for MediKiosk. Convert the following structured patient answers "
        f"and spoken statements into a concise, accurate, professional History of Present Illness (HPI) paragraph for the attending physician.\n"
        f"Rules:\n"
        f"1. Rely ONLY on the verified fields and patient statements provided below. Do not invent unmentioned facts.\n"
        f"2. Integrate chief complaint, onset, severity, associated symptoms, past medical history, and drug allergies into a coherent narrative.\n"
        f"3. Use professional medical terminology.\n"
        f"4. Output ONLY the plain text paragraph.\n\n"
        f"Patient data:\n{json.dumps(payload, indent=2)}\n\n"
        f"Language requested: {lang}"
    )
    result = _call_gemini_text(prompt, temperature=0.2)
    return result if result else _template_hpi(fields, answer_meta)

