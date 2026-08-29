"""Module B — medical document digitization (upload -> OCR -> structured entities).

Lane 5 - T1: Real OCR extraction for printed prescriptions and lab reports.
Uses Tesseract for OCR and regex-based entity extraction to flag abnormal values.
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..ocr.extractor import extract_document, extract_entities, run_ocr
from ..store import session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/session", tags=["documents"])


def _require(session_id: str) -> dict:
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or already cleared.")
    return session


def _extract(filename: str, file_bytes: bytes, mime_type: str = "") -> dict:
    """Digitize medical document using Gemini Vision or smart local fallback."""
    return extract_document(file_bytes=file_bytes, filename=filename, mime_type=mime_type)



def _stub_extract(filename: str) -> dict:
    """Fallback stub extractor for when OCR fails or isn't configured."""
    name = (filename or "").lower()
    if "lab" in name or "report" in name or "blood" in name:
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
        }
    return {
        "type": "prescription",
        "date": "2026-06-15",
        "ocr_confidence": 0.83,
        "entities": {
            "diagnoses": ["Type 2 Diabetes Mellitus", "Hypertension"],
            "medications": [
                {"name": "Metformin", "dose": "500 mg", "frequency": "BD"},
                {"name": "Amlodipine", "dose": "5 mg", "frequency": "OD"},
            ],
            "investigations": [],
        },
    }


@router.post("/{session_id}/documents")
async def upload_document(session_id: str, file: UploadFile = File(...)) -> dict:
    session = _require(session_id)

    # Read file bytes
    file_bytes = await file.read()

    # Run extraction (Gemini Vision / local fallback)
    doc = _extract(file.filename or "", file_bytes, mime_type=file.content_type or "")
    doc["doc_id"] = uuid.uuid4().hex
    doc["source_filename"] = file.filename
    session["documents"].append(doc)
    session_store.save_session(session)

    return doc



@router.get("/{session_id}/documents")
def list_documents(session_id: str) -> dict:
    session = _require(session_id)
    docs = sorted(session.get("documents", []), key=lambda d: d.get("date") or "", reverse=True)
    return {"documents": docs, "count": len(docs)}
