"""Session lifecycle: create, consent, snapshot, submit (with FHIR + privacy clear)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..core import dialogue_engine, fhir_builder, summary_builder
from ..models.schemas import ConsentRequest, CreateSessionRequest
from ..store import audit_log, session_store

router = APIRouter(prefix="/api/session", tags=["session"])


def _require(session_id: str) -> dict:
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or already cleared.")
    return session


@router.post("")
def create_session(body: CreateSessionRequest) -> dict:
    session = session_store.create_session(language=body.language)
    question = dialogue_engine.current_question(session)   # sets entry node
    session_store.save_session(session)
    audit_log.record(session["id"], actor="system", action="create", resource="session", purpose="care")
    return {
        "session_id": session["id"],
        "language": session["language"],
        "question": question,
    }


@router.post("/{session_id}/consent")
def give_consent(session_id: str, body: ConsentRequest) -> dict:
    session = _require(session_id)
    from datetime import datetime, timezone

    session["consent"] = {
        "given": body.given,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    session_store.save_session(session)
    audit_log.record(session_id, actor="patient", action="consent", resource="session", purpose="consent")
    return {"session_id": session_id, "consent": session["consent"]}


@router.get("/{session_id}")
def get_session(session_id: str) -> dict:
    session = _require(session_id)
    return {
        "session_id": session["id"],
        "language": session["language"],
        "status": session["status"],
        "current_node": session["current_node"],
        "answers": session["answers"],
        "red_flags": session["red_flags"],
        "consent": session["consent"],
        "document_count": len(session.get("documents", [])),
    }


@router.post("/{session_id}/submit")
def submit(session_id: str, clear: bool = Query(False, description="Delete session data after submit (privacy)")) -> dict:
    session = _require(session_id)
    summary = summary_builder.build_summary(session)
    abha = (session.get("consent") or {}).get("abha_id")
    bundle = fhir_builder.build_bundle(session, summary, abha_id=abha)
    audit_log.record(session_id, actor="clinician", action="export", resource="fhir_bundle", purpose="care")

    result = {
        "session_id": session_id,
        "summary": summary,
        "fhir_bundle": bundle,
        "pushed_to_abdm": False,   # mocked: real ABDM sandbox push is a production step
        "note": "FHIR bundle generated. ABDM sandbox push is stubbed for the demo.",
        "cleared": False,
    }
    if clear:
        audit_log.record(session_id, actor="system", action="erase", resource="session", purpose="rights")
        session_store.delete_session(session_id)   # temporary data cleared after submit
        result["cleared"] = True
    return result
