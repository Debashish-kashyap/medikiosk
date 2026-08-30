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
import os
import re
from typing import Any

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

    # 3. Multi-select and Single-select matching
    result = _interpret_aliases(node, text_norm, lang)

    # Optional real LLM only if aliases were ambiguous AND a model is configured.
    if USE_LLM and result["confidence"] < 0.55:
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
    """Return match confidence between a candidate alias/label and input text.
    Handles exact, word boundary, partial (50% heard), word overlap, and fuzzy matches.
    """
    c = cand.strip().lower()
    t = text.strip().lower()
    if not c or not t:
        return 0.0

    # 1. Exact match
    if c == t:
        return 0.98

    # 2. Exact whole-word boundary match
    escaped = re.escape(c)
    pattern = rf"(?:^|\W){escaped}(?:$|\W)"
    if re.search(pattern, t):
        return 0.92 if len(c) > 2 else 0.82

    # 3. Substring match (candidate in text, e.g. 'chest' in 'I have chest pain')
    if c in t:
        ratio = len(c) / len(t)
        return max(0.82, 0.72 + 0.25 * ratio)

    # 4. Partial word heard (text in candidate, e.g. 'chest' in 'chest pain' or 'diab' in 'diabetes')
    if t in c:
        ratio = len(t) / len(c)
        if ratio >= 0.50:  # 50% heard
            return max(0.80, 0.68 + 0.30 * ratio)
        elif ratio >= 0.30 and len(t) >= 3:
            return 0.65

    # 5. Word-by-word overlap (e.g. 'blood pressure' vs 'high blood pressure')
    c_words = [w for w in re.split(r"\W+", c) if len(w) > 1]
    t_words = [w for w in re.split(r"\W+", t) if len(w) > 1]
    if c_words and t_words:
        common_words = set(c_words) & set(t_words)
        if common_words:
            overlap = len(common_words) / min(len(c_words), len(t_words))
            if overlap >= 0.50:
                return 0.88

    # 6. Fuzzy string similarity (full phrase typos)
    sim = difflib.SequenceMatcher(None, c, t).ratio()
    if sim >= 0.70:
        return round(0.60 + (sim - 0.70) * 0.80, 2)

    # 7. Fuzzy word-to-word similarity (single word typo e.g. 'fevr' vs 'fever')
    if c_words and t_words:
        max_word_sim = max(difflib.SequenceMatcher(None, cw, tw).ratio() for cw in c_words for tw in t_words)
        if max_word_sim >= 0.75:
            return round(0.60 + (max_word_sim - 0.75) * 0.80, 2)

    return 0.0


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
    """Call Google AI Studio Gemini API for text generation."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured")

    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    # Try google.genai SDK first (new, recommended)
    try:
        import google.genai as genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=temperature,
            ),
        )
        return response.text.strip()
    except ImportError:
        logger.info("google.genai SDK not found; trying google-generativeai...")
    except Exception as e:
        logger.warning("google.genai call failed (%s)", e)

    # Fallback to google.generativeai SDK (deprecated but still works)
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_instance = genai.GenerativeModel(model)
        resp = model_instance.generate_content(prompt)
        return resp.text.strip()
    except ImportError:
        logger.info("google-generativeai SDK not found; using direct REST API")
    except Exception as e:
        logger.warning("Legacy SDK call failed (%s)", e)

    # Direct REST API call
    import httpx
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("No candidate in Gemini response")
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise RuntimeError("Empty response parts from Gemini")
    return parts[0].get("text", "").strip()


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


def phrase_hpi(narrative_fields: dict[str, Any], lang: str = "en") -> str:
    """Phrase the History of Present Illness from verified fields."""
    if USE_LLM or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
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
    """Generate concise, professional clinical HPI narrative using Gemini."""
    import json
    prompt = (
        f"You are a clinical documentation assistant for MediKiosk. Convert the following structured patient answers "
        f"into a concise, accurate 2-3 sentence History of Present Illness (HPI) paragraph for the attending physician.\n"
        f"Rules:\n"
        f"1. Rely ONLY on the verified fields provided below. Do not invent any unmentioned facts.\n"
        f"2. Use professional medical terminology.\n"
        f"3. Output ONLY the plain text paragraph.\n\n"
        f"Patient answers:\n{json.dumps(fields, indent=2)}\n\n"
        f"Language requested: {lang}"
    )
    result = _call_gemini_text(prompt, temperature=0.2)
    return result if result else _template_hpi(fields)

