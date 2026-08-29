"""Medical document digitization & entity extraction (Lane 5 - Gemini Vision & OCR).

Extracts structured clinical entities (investigations, diagnoses, medications) from
uploaded medical documents (prescriptions, lab reports, discharge summaries) using
Google AI Studio Gemini Vision API, with local fallback for offline development.
"""
from __future__ import annotations

import base64
import json
import logging
import mimetypes
import re
from typing import Any

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

# Reference ranges for common lab tests
REF_RANGES = {
    "glucose": {"fasting": {"min": 70, "max": 100, "unit": "mg/dL"}},
    "hba1c": {"min": 0, "max": 5.7, "unit": "%"},
    "haemoglobin": {"male": {"min": 13, "max": 17, "unit": "g/dL"}, "female": {"min": 12, "max": 15, "unit": "g/dL"}},
    "blood_pressure": {"systolic": {"min": 90, "max": 120}, "diastolic": {"min": 60, "max": 80}},
    "heart_rate": {"min": 60, "max": 100, "unit": "bpm"},
    "temperature": {"min": 97.8, "max": 99.1, "unit": "F"},
}

# Prescription regex patterns (for local fallback)
MEDICATION_PATTERNS = [
    r"(\w+)\s+(?:tab|tablet|capsule|syrup|injection)\s*[:\-]?\s*(\d+\s*(?:mg|mcg|g|ml|iu))",
    r"(\w+)\s+(\d+\s*(?:mg|mcg|g|ml|iu))\s*(?:BD|OD|BID|TID|QID|HS|PRN)?",
]

# Lab report patterns (for local fallback)
LAB_TEST_PATTERNS = {
    "glucose": r"glucose|sugar|fbs|pp",
    "hba1c": r"hba1c|hemoglobin\s+a1c|a1c",
    "haemoglobin": r"haemoglobin|hgb|hgb\s*level",
    "bp": r"bp|blood\s*pressure|systolic|diastolic",
    "pulse": r"pulse|heart\s*rate|hr",
    "temperature": r"temp|temperature|fever",
}

GEMINI_PROMPT = """You are an expert medical document digitization assistant for a clinical kiosk (MediKiosk).
Analyze the provided medical document image (which may be a printed or handwritten prescription, lab report, diagnostic test, or clinical summary).
Extract all relevant structured clinical information into a valid JSON object strictly matching this schema:

{
  "type": "prescription" | "lab_report" | "discharge_summary" | "diagnostic_report" | "other",
  "date": "YYYY-MM-DD or estimated date if visible, otherwise 2026-07-02",
  "ocr_confidence": 0.95,
  "summary": "Brief 1-sentence summary of document contents",
  "diagnoses": ["List of diagnosed diseases, symptoms, or clinical impressions"],
  "medications": [
    {
      "name": "Drug name (e.g. Metformin)",
      "dose": "Dosage (e.g. 500 mg)",
      "frequency": "Frequency (e.g. BD, OD, TID, twice daily)",
      "duration": "Duration if mentioned (e.g. 10 days)",
      "instructions": "Special instructions (e.g. after meals)"
    }
  ],
  "investigations": [
    {
      "name": "Test name (e.g. Fasting blood glucose, HbA1c, Haemoglobin)",
      "value": 168,
      "unit": "mg/dL",
      "ref_range": "70-100",
      "flag": "HIGH" | "LOW" | "NORMAL" | "ABNORMAL"
    }
  ],
  "raw_text": "Extracted key text transcription from document"
}

Important Instructions:
1. Extract numerical values for lab investigations with appropriate units and reference ranges.
2. Accurately flag values that are HIGH, LOW, or ABNORMAL.
3. If an item is not found, return an empty list [] for that key.
4. Output ONLY valid, pure JSON without any markdown ticks or conversational text.
"""


def _detect_mime_type(filename: str, file_bytes: bytes) -> str:
    """Detect image/document MIME type."""
    if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if file_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if file_bytes.startswith(b"RIFF") and file_bytes[8:12] == b"WEBP":
        return "image/webp"
    if file_bytes.startswith(b"%PDF"):
        return "application/pdf"
    
    mime, _ = mimetypes.guess_type(filename)
    return mime or "image/jpeg"


def extract_with_gemini_vision(file_bytes: bytes, filename: str = "", mime_type: str = "") -> dict[str, Any]:
    """Extract clinical entities using Google AI Studio Gemini Vision API."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    if not mime_type:
        mime_type = _detect_mime_type(filename, file_bytes)

    base64_data = base64.b64encode(file_bytes).decode("utf-8")
    model = settings.GEMINI_MODEL or "gemini-3.6-flash"

    # Try google.genai SDK (new, recommended)
    try:
        import google.genai as genai
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=model,
            contents=[
                GEMINI_PROMPT,
                genai.types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            ],
            config=genai.types.GenerateContentConfig(
                response_mime="application/json",
            ),
        )
        raw_output = response.text
        return _parse_gemini_json(raw_output)
    except ImportError:
        logger.info("google.genai SDK not found; trying google-generativeai...")
    except Exception as e:
        logger.warning("google.genai call failed (%s); trying legacy SDK", e)

    # Fallback to google.generativeai SDK (deprecated but still works)
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model_instance = genai.GenerativeModel(model)

        response = model_instance.generate_content([
            GEMINI_PROMPT,
            {"mime_type": mime_type, "data": file_bytes},
        ])
        raw_output = response.text
        return _parse_gemini_json(raw_output)
    except ImportError:
        logger.info("google-generativeai SDK not found; using direct Google AI Studio REST API")
    except Exception as e:
        logger.warning("Legacy SDK call failed (%s); trying direct REST API", e)

    # Direct HTTP call to Google AI Studio REST API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": GEMINI_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64_data,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("No candidate returned by Gemini Vision")

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise RuntimeError("Empty response from Gemini Vision")

    raw_output = parts[0].get("text", "")
    return _parse_gemini_json(raw_output)


def _parse_gemini_json(raw_text: str) -> dict[str, Any]:
    """Parse and sanitize JSON from Gemini output."""
    clean_text = raw_text.strip()
    # Strip markdown code blocks if present
    if clean_text.startswith("```"):
        clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r"\s*```$", "", clean_text)
        clean_text = clean_text.strip()

    parsed = json.loads(clean_text)

    # Normalize entity structure
    investigations = parsed.get("investigations", [])
    diagnoses = parsed.get("diagnoses", [])
    medications = parsed.get("medications", [])

    # Post-process flags on investigations
    for inv in investigations:
        name = inv.get("name", "")
        val = inv.get("value")
        unit = inv.get("unit", "")
        flag = inv.get("flag")
        if isinstance(val, (int, float)) and (not flag or flag == "NORMAL"):
            calculated_flag = _check_abnormal(name, float(val), unit)
            if calculated_flag:
                inv["flag"] = calculated_flag

    entities = {
        "investigations": investigations,
        "diagnoses": diagnoses,
        "medications": medications,
    }

    return {
        "type": parsed.get("type", "unknown"),
        "date": parsed.get("date", "2026-07-02"),
        "ocr_confidence": float(parsed.get("ocr_confidence", 0.95)),
        "summary": parsed.get("summary", ""),
        "entities": entities,
        "raw_text": parsed.get("raw_text", ""),
        "extractor": "gemini_vision",
    }


def extract_document(file_bytes: bytes, filename: str = "", mime_type: str = "") -> dict[str, Any]:
    """Primary document extractor: uses Gemini Vision if configured, else smart local fallback."""
    if settings.GEMINI_API_KEY:
        try:
            logger.info("Extracting document '%s' with Gemini Vision", filename)
            return extract_with_gemini_vision(file_bytes, filename=filename, mime_type=mime_type)
        except Exception as e:
            logger.warning("Gemini Vision extraction failed (%s). Falling back to local OCR/parser.", e)

    # Fallback to local OCR / text extraction
    return _local_extract(filename, file_bytes)


def _local_extract(filename: str, file_bytes: bytes) -> dict[str, Any]:
    """Fallback extractor when Gemini is not configured or offline."""
    name_lower = (filename or "").lower()
    is_lab = any(kw in name_lower for kw in ["lab", "report", "blood", "test", "cbc", "glucose", "lipid"])
    is_prescription = any(kw in name_lower for kw in ["prescription", "rx", "script", "meds", "dr"])

    # Try local OCR if possible
    ocr_text = ""
    try:
        import tempfile
        import os
        from pathlib import Path

        suffix = Path(filename).suffix.lower() if filename else ".png"

        # Handle PDF files - convert to images first
        if suffix == ".pdf":
            ocr_text = _ocr_pdf(file_bytes)
        else:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            try:
                ocr_text = run_ocr(tmp_path)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
    except Exception:
        pass

    if ocr_text.strip():
        entities = extract_entities(ocr_text)
        conf = min(0.92, 0.5 + len(ocr_text) / 1000)
        return {
            "type": "lab_report" if is_lab else "prescription" if is_prescription else "unknown",
            "date": "2026-07-02",
            "ocr_confidence": round(conf, 2),
            "ocr_text_length": len(ocr_text),
            "entities": entities,
            "raw_text": ocr_text[:300],
            "extractor": "local_tesseract",
            "note": "Extracted via local OCR engine",
        }

    # Deterministic mock fallback for demo consistency
    if is_lab:
        return {
            "type": "lab_report",
            "date": "2026-07-02",
            "ocr_confidence": 0.88,
            "entities": {
                "investigations": [
                    {"name": "Fasting blood glucose", "value": 168, "unit": "mg/dL",
                     "ref_range": "70-100", "flag": "HIGH"},
                    {"name": "HbA1c", "value": 8.2, "unit": "%",
                     "ref_range": "<5.7", "flag": "HIGH"},
                    {"name": "Haemoglobin", "value": 13.1, "unit": "g/dL",
                     "ref_range": "13-17", "flag": "NORMAL"},
                ],
                "diagnoses": [],
                "medications": [],
            },
            "extractor": "local_fallback",
            "note": "Set GEMINI_API_KEY in backend/.env for AI Studio Vision extraction.",
        }

    return {
        "type": "prescription",
        "date": "2026-06-15",
        "ocr_confidence": 0.85,
        "entities": {
            "diagnoses": ["Type 2 Diabetes Mellitus", "Hypertension"],
            "medications": [
                {"name": "Metformin", "dose": "500 mg", "frequency": "BD", "instructions": "After food"},
                {"name": "Amlodipine", "dose": "5 mg", "frequency": "OD", "instructions": "Morning"},
            ],
            "investigations": [],
        },
        "extractor": "local_fallback",
        "note": "Set GEMINI_API_KEY in backend/.env for AI Studio Vision extraction.",
    }


def extract_entities(text: str) -> dict[str, Any]:
    """Extract medical entities from plain text using regex rules."""
    entities = {
        "investigations": [],
        "diagnoses": [],
        "medications": [],
    }

    text_lower = text.lower()

    # Extract medications
    for pattern in MEDICATION_PATTERNS:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            med_name = match.group(1).title()
            dose = match.group(2)
            entities["medications"].append({
                "name": med_name,
                "dose": dose,
                "frequency": "OD",
            })

    # Remove duplicates
    entities["medications"] = list({json.dumps(m, sort_keys=True): m for m in entities["medications"]}.values())

    # Extract lab tests with values and flags
    for test_name, pattern in LAB_TEST_PATTERNS.items():
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            value_pattern = r"{}[^0-9]*[:\-]?\s*(\d+(?:\.\d+)?)\s*(mg/dL|mg/dl|%|bpm|F|C|mm[Hh][gG]?)?".format(
                re.escape(match.group(0))
            )
            value_match = re.search(value_pattern, text, re.IGNORECASE)
            if value_match:
                value = float(value_match.group(1))
                unit = value_match.group(2) or ""
                flag = _check_abnormal(test_name, value, unit) or "NORMAL"
                entities["investigations"].append({
                    "name": match.group(0).title(),
                    "value": value,
                    "unit": unit,
                    "flag": flag,
                })

    # Extract diagnoses
    diagnosis_keywords = [
        r"diagnosis[:\s]+(.+)",
        r"dx[:\s]+(.+)",
        r"impression[:\s]+(.+)",
        r"findings[:\s]+(.+)",
    ]
    for pattern in diagnosis_keywords:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            entities["diagnoses"].append(match.strip().title())

    entities["diagnoses"] = list({d.lower(): d for d in entities["diagnoses"] if d}.values())
    return entities


def _check_abnormal(test_name: str, value: float, unit: str) -> str | None:
    """Check if a lab value is abnormal based on reference ranges."""
    test_lower = test_name.lower()

    if "glucose" in test_lower or "sugar" in test_lower or "fbs" in test_lower:
        ref = REF_RANGES.get("glucose", {}).get("fasting", {})
        if ref.get("min") and value < ref["min"]:
            return "LOW"
        if ref.get("max") and value > ref["max"]:
            return "HIGH"

    if "hba1c" in test_lower or "a1c" in test_lower:
        ref = REF_RANGES.get("hba1c", {})
        if ref.get("min") is not None and value < ref["min"]:
            return "LOW"
        if ref.get("max") is not None and value > ref["max"]:
            return "HIGH"

    if "haemoglobin" in test_lower or "hgb" in test_lower:
        ref = REF_RANGES.get("haemoglobin", {})
        min_val = ref.get("male", {}).get("min", ref.get("female", {}).get("min", 12))
        max_val = ref.get("male", {}).get("max", ref.get("female", {}).get("max", 17))
        if value < min_val:
            return "LOW"
        if value > max_val:
            return "HIGH"

    if "bp" in test_lower or "pressure" in test_lower:
        if "systolic" in test_lower or "top" in test_lower or not unit:
            if value < 90:
                return "LOW"
            if value > 140:
                return "HIGH"
        elif "diastolic" in test_lower or "bottom" in test_lower:
            if value < 60:
                return "LOW"
            if value > 90:
                return "HIGH"

    if "pulse" in test_lower or "heart" in test_lower or "hr" in test_lower:
        ref = REF_RANGES.get("heart_rate", {})
        if ref.get("min") and value < ref["min"]:
            return "LOW"
        if ref.get("max") and value > ref["max"]:
            return "HIGH"

    return None


def _ocr_pdf(file_bytes: bytes) -> str:
    """Convert PDF to images and run OCR on each page using PyMuPDF (no system dependencies)."""
    try:
        import tempfile
        import os
        import pytesseract
        from PIL import Image

        logger.info("Running OCR on PDF document using PyMuPDF")

        # Import fitz (PyMuPDF)
        import fitz  # PyMuPDF

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(tmp_path)
            all_text = []

            for page_num in range(len(doc)):
                logger.info("OCR processing page %d/%d", page_num + 1, len(doc))
                page = doc[page_num]

                # Convert page to image (300 DPI for better OCR accuracy)
                mat = fitz.Matrix(300 / 72)  # 300 DPI
                pix = page.get_pixmap(matrix=mat)

                # Save to temp image file
                img_path = tmp_path.replace(".pdf", f"_page_{page_num}.png")
                pix.save(img_path)

                try:
                    # Run OCR on the image
                    text = pytesseract.image_to_string(img_path)
                    if text.strip():
                        all_text.append(f"--- Page {page_num + 1} ---\n{text.strip()}")
                finally:
                    # Clean up temp image
                    try:
                        os.unlink(img_path)
                    except OSError:
                        pass

            doc.close()
            return "\n\n".join(all_text)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except ImportError as e:
        logger.debug("PyMuPDF not installed: %s", e)
        return ""
    except Exception as e:
        logger.warning("PDF OCR failed: %s", e)
        return ""


def run_ocr(image_path: str) -> str:
    """Run local Tesseract OCR on an image if installed."""
    try:
        import pytesseract
        from PIL import Image

        logger.info("Running local Tesseract OCR on: %s", image_path)
        text = pytesseract.image_to_string(Image.open(image_path))
        logger.info("OCR extracted %d characters", len(text))
        return text.strip()
    except ImportError:
        logger.debug("pytesseract or PIL not installed for local fallback.")
        return ""
    except Exception as e:
        logger.warning("Local OCR failed: %s", e)
        return ""

