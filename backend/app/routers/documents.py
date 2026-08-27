"""Module B — medical document digitization (upload -> OCR -> structured entities).

DEMO NOTE: this returns a realistic STUB extraction so the end-to-end flow and the
physician timeline/abnormal-value highlighting work today. The AI-NLU/OCR lane replaces
`_extract` with: Tesseract / cloud OCR (printed docs) -> entity extraction (LLM/regex)
-> abnormal-value flagging against reference ranges. Handwriting is a roadmap item.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..store import session_store

router = APIRouter(prefix="/api/session", tags=["documents"])


def _require(session_id: str) -> dict:
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or already cleared.")
    return session


def _extract(filename: str) -> dict:
    """STUB extractor. Returns a lab report for files hinting 'lab', else a prescription."""
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
    await file.read()   # PRODUCTION: pass bytes to OCR instead of discarding
    doc = _extract(file.filename or "")
    doc["doc_id"] = uuid.uuid4().hex
    doc["source_filename"] = file.filename
    doc["note"] = "Stub OCR extraction — wire Tesseract/cloud OCR + entity model here."
    session["documents"].append(doc)
    session_store.save_session(session)
    return doc


@router.get("/{session_id}/documents")
def list_documents(session_id: str) -> dict:
    session = _require(session_id)
    docs = sorted(session.get("documents", []), key=lambda d: d.get("date") or "", reverse=True)
    return {"documents": docs, "count": len(docs)}
