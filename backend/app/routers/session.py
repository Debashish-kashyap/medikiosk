"""Session lifecycle: create, consent, snapshot, submit (with FHIR + privacy clear)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..core import abha_service, dialogue_engine, fhir_builder, summary_builder
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
    session = session_store.create_session(language=body.language, ayush_mode=body.ayush_mode)
    question = dialogue_engine.current_question(session)   # sets entry node
    session_store.save_session(session)
    audit_log.record(session["id"], actor="system", action="create", resource="session", purpose="care")
    return {
        "session_id": session["id"],
        "language": session["language"],
        "ayush_mode": session.get("ayush_mode", False),
        "question": question,
    }


@router.post("/{session_id}/consent")
def give_consent(session_id: str, body: ConsentRequest) -> dict:
    session = _require(session_id)
    from datetime import datetime, timezone

    if body.given and not body.abha_id:
        raise HTTPException(status_code=422, detail="ABHA ID is required before collecting health information.")

    session["consent"] = {
        "given": body.given,
        "ts": datetime.now(timezone.utc).isoformat(),
        "abha_linked": False,
    }
    if body.given and body.abha_id:
        try:
            abha_service.link_abha(session_id, body.abha_id, body.otp)
            session["consent"]["abha_linked"] = True
            session["consent"]["abha_id"] = body.abha_id.strip()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError:
            raise HTTPException(status_code=502, detail="ABHA verification is temporarily unavailable.")
    session_store.save_session(session)
    audit_log.record(session_id, actor=f"patient:{session_id}", role="patient", action="ABHA_LINK" if body.abha_id else "CONSENT", resource="session", success=True, purpose="consent")
    return {"session_id": session_id, "consent": session["consent"]}


@router.get("/{session_id}")
def get_session(session_id: str) -> dict:
    session = _require(session_id)
    return {
        "session_id": session["id"],
        "language": session["language"],
        "ayush_mode": session.get("ayush_mode", False),
        "ayush_done": session.get("ayush_done", False),
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
    abha = (abha_service.get_abha_link(session_id) or {}).get("abha_id")
    bundle = fhir_builder.build_bundle(session, summary, abha_id=abha)
    pushed = False
    if (session.get("permissions") or {}).get("abdm_share"):
        try:
            pushed = fhir_builder.push_to_abdm_sandbox(bundle)
        except RuntimeError:
            audit_log.record(session_id, actor="system", role="system", action="FHIR_EXPORT", resource="fhir_bundle", success=False, purpose="abdm_share")
            raise HTTPException(status_code=502, detail="ABDM sandbox export is temporarily unavailable.")
    audit_log.record(session_id, actor="clinician", role="physician", action="FHIR_EXPORT", resource="fhir_bundle", success=True, purpose="care")

    result = {
        "session_id": session_id,
        "summary": summary,
        "fhir_bundle": bundle,
        "pushed_to_abdm": pushed,
        "note": "FHIR bundle generated. ABDM sandbox export occurs only after explicit sharing consent and sandbox configuration.",
        "cleared": False,
    }
    if clear:
        audit_log.record(session_id, actor="system", action="erase", resource="session", purpose="rights")
        session_store.delete_session(session_id)   # temporary data cleared after submit
        result["cleared"] = True
    return result
