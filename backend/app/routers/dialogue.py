"""Dialogue: fetch the current question, submit an answer (voice or touch)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..core import dialogue_engine
from ..models.schemas import AnswerRequest
from ..store import audit_log, session_store

router = APIRouter(prefix="/api/session", tags=["dialogue"])


def _require(session_id: str) -> dict:
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or already cleared.")
    return session


@router.get("/{session_id}/next")
def next_question(session_id: str) -> dict:
    session = _require(session_id)
    question = dialogue_engine.current_question(session)
    session_store.save_session(session)
    if question is None:
        return {"done": True, "summary_ready": True, "question": None}
    return {"done": False, "question": question}


@router.post("/{session_id}/answer")
def answer(session_id: str, body: AnswerRequest) -> dict:
    session = _require(session_id)
    if not session.get("consent", {}).get("given"):
        audit_log.record(session_id, actor=f"patient:{session_id}", role="patient", action="ACCESS_DENIED", resource="questionnaire", success=False, purpose="consent")
        raise HTTPException(status_code=403, detail="Consent is required before collecting health information.")
    result = dialogue_engine.process_answer(
        session,
        node_id=body.node_id,
        touch_value=body.touch_value,
        text=body.text,
        confidence=body.confidence,
        confirmed=body.confirmed,
    )
    session_store.save_session(session)
    if result.get("status") == "error":
        audit_log.record(session_id, actor=f"patient:{session_id}", role="patient", action="UPDATE_PATIENT_RECORD", resource=body.node_id, success=False, purpose="care")
        raise HTTPException(status_code=400, detail=result["message"])
    action = "ANSWER_REQUIRES_CONFIRMATION" if result.get("status") == "needs_confirmation" else "UPDATE_PATIENT_RECORD"
    audit_log.record(session_id, actor=f"patient:{session_id}", role="patient", action=action, resource=body.node_id, success=True, purpose="care")
    return result
