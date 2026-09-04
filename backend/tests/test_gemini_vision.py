"""Tests for Lane 5 - Gemini Vision document extraction & NLU."""
import io
import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ocr.extractor import (
    _check_abnormal,
    _detect_mime_type,
    _parse_gemini_json,
    extract_document,
    extract_entities,
)
from app.core import llm_mapper


@pytest.fixture
def client():
    return TestClient(app)


def test_detect_mime_type():
    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
    jpeg_header = b"\xff\xd8\xff" + b"\x00" * 20
    pdf_header = b"%PDF-1.4" + b"\x00" * 20

    assert _detect_mime_type("test.png", png_header) == "image/png"
    assert _detect_mime_type("test.jpg", jpeg_header) == "image/jpeg"
    assert _detect_mime_type("test.pdf", pdf_header) == "application/pdf"
    assert _detect_mime_type("report.png", b"unknownbytes") == "image/png"


def test_check_abnormal_flags():
    # Glucose fasting
    assert _check_abnormal("Fasting Blood Sugar", 168.0, "mg/dL") == "HIGH"
    assert _check_abnormal("glucose", 55.0, "mg/dL") == "LOW"
    assert _check_abnormal("glucose", 85.0, "mg/dL") is None

    # HbA1c
    assert _check_abnormal("HbA1c", 8.2, "%") == "HIGH"
    assert _check_abnormal("HbA1c", 5.2, "%") is None

    # Haemoglobin
    assert _check_abnormal("Haemoglobin", 10.5, "g/dL") == "LOW"
    assert _check_abnormal("Haemoglobin", 14.5, "g/dL") is None


def test_parse_gemini_json():
    sample_response = """
    ```json
    {
      "type": "lab_report",
      "date": "2026-07-02",
      "ocr_confidence": 0.96,
      "summary": "Elevated fasting blood glucose and HbA1c indicating uncontrolled hyperglycemia.",
      "diagnoses": ["Type 2 Diabetes"],
      "medications": [
        {"name": "Metformin", "dose": "500 mg", "frequency": "BD", "instructions": "After food"}
      ],
      "investigations": [
        {"name": "Fasting Blood Glucose", "value": 172, "unit": "mg/dL", "ref_range": "70-100", "flag": "HIGH"},
        {"name": "HbA1c", "value": 8.4, "unit": "%", "ref_range": "<5.7", "flag": "HIGH"},
        {"name": "Haemoglobin", "value": 14.0, "unit": "g/dL", "ref_range": "13-17", "flag": "NORMAL"}
      ],
      "raw_text": "Patient: Jane Doe. FBS: 172 mg/dL. HbA1c: 8.4%. Rx: Metformin 500mg BD."
    }
    ```
    """
    result = _parse_gemini_json(sample_response)
    assert result["type"] == "lab_report"
    assert result["date"] == "2026-07-02"
    assert result["ocr_confidence"] == 0.96
    assert result["extractor"] == "gemini_vision"
    assert len(result["entities"]["investigations"]) == 3
    assert len(result["entities"]["medications"]) == 1
    assert result["entities"]["medications"][0]["name"] == "Metformin"
    assert result["entities"]["investigations"][0]["flag"] == "HIGH"


def test_fallback_local_extraction():
    # Test fallback when no API key is provided
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    result = extract_document(fake_png, filename="blood_report.png")
    assert result["type"] == "lab_report"
    assert "entities" in result
    assert "investigations" in result["entities"]
    assert len(result["entities"]["investigations"]) > 0


def test_extract_entities_regex():
    sample_text = (
        "Prescription:\n"
        "Dx: Hypertension and Diabetes Mellitus\n"
        "Tab Metformin 500 mg BD\n"
        "Tab Amlodipine 5 mg OD\n"
        "Lab results: Glucose: 160 mg/dL, HbA1c: 7.8 %\n"
    )
    entities = extract_entities(sample_text)
    assert len(entities["medications"]) >= 2
    assert any(m["name"] == "Metformin" for m in entities["medications"])
    assert any(m["name"] == "Amlodipine" for m in entities["medications"])
    assert len(entities["investigations"]) >= 1


def test_document_upload_api_flow(client):
    # 1. Create session
    start_resp = client.post("/api/session", json={"language": "en"})
    assert start_resp.status_code == 200
    session_id = start_resp.json()["session_id"]


    # 2. Upload document
    file_content = b"\x89PNG\r\n\x1a\n" + b"dummy-medical-doc-bytes"
    upload_resp = client.post(
        f"/api/session/{session_id}/documents",
        files={"file": ("lab_report.png", file_content, "image/png")},
    )
    assert upload_resp.status_code == 200
    doc_data = upload_resp.json()
    assert "doc_id" in doc_data
    assert doc_data["source_filename"] == "lab_report.png"
    assert "entities" in doc_data

    # 3. Retrieve documents
    list_resp = client.get(f"/api/session/{session_id}/documents")
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] == 1


def test_phrase_hpi_template_fallback():
    fields = {
        "chief_complaint": "chest_pain",
        "cp_site": "retrosternal",
        "cp_character": "pressure",
        "cp_onset": "gradual",
        "cp_radiation": "left_arm",
        "cp_breathless": "yes",
        "cp_sweating": "yes",
        "cp_severity": 8,
    }
    hpi = llm_mapper.phrase_hpi(fields, lang="en")
    assert ("Patient presents with chest pain" in hpi or "Patient reports chest pain" in hpi)
    assert "retrosternal" in hpi
    assert "pressure" in hpi
    assert "left arm" in hpi
    assert "8/10" in hpi
