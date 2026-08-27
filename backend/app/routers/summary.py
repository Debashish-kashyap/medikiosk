"""Module C summary + FHIR views (read-only; final push is /session/{id}/submit)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..core import fhir_builder, summary_builder
from ..store import audit_log, session_store

router = APIRouter(prefix="/api/session", tags=["summary"])


def _require(session_id: str) -> dict:
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or already cleared.")
    return session


@router.get("/{session_id}/summary")
def get_summary(session_id: str) -> dict:
    session = _require(session_id)
    audit_log.record(session_id, actor="clinician", action="view", resource="summary", purpose="care")
    return summary_builder.build_summary(session)


@router.get("/{session_id}/fhir")
def get_fhir(session_id: str) -> dict:
    session = _require(session_id)
    audit_log.record(session_id, actor="clinician", action="view", resource="fhir_bundle", purpose="care")
    summary = summary_builder.build_summary(session)
    return fhir_builder.build_bundle(session, summary)
