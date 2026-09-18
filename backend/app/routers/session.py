"""Session lifecycle: create, consent, snapshot, submit (with FHIR + privacy clear)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..config import settings
from ..core import abha_service, dialogue_engine, fhir_builder, identity_service, summary_builder
from ..models.schemas import ConsentRequest, CreateSessionRequest, RouteRequest
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

    session["consent"] = {
        "given": body.given,
        "ts": datetime.now(timezone.utc).isoformat(),
        "abha_linked": False,
        "identity_type": body.identity_type if body.given else None,
    }
    if body.given:
        try:
            if body.identity_type == "abha":
                abha_service.link_abha(session_id, body.identity_value, body.otp)
                session["consent"]["abha_linked"] = True
                session["consent"]["abha_id"] = body.identity_value
            else:
                session["consent"]["identity"] = identity_service.verify_local_identity(
                    identity_type=body.identity_type,
                    identity_value=body.identity_value,
                    full_name=body.full_name,
                    mobile_number=body.mobile_number,
                )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError:
            raise HTTPException(status_code=502, detail="ABHA verification is temporarily unavailable.")
    session_store.save_session(session)
    audit_log.record(session_id, actor=f"patient:{session_id}", role="patient", action="IDENTITY_VERIFY" if body.given else "CONSENT", resource="session", success=True, purpose="consent")
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
    routing = _route_bundle(session_id, session, bundle, ["his", "abdm"])
    audit_log.record(session_id, actor="clinician", role="physician", action="FHIR_EXPORT", resource="fhir_bundle", success=True, purpose="care")

    result = {
        "session_id": session_id,
        "summary": summary,
        "fhir_bundle": bundle,
        "pushed_to_abdm": routing["abdm"]["pushed"],
        "routing": routing,
        "note": "FHIR bundle generated. External delivery is reported per configured destination and sharing permission.",
        "cleared": False,
    }
    if clear:
        audit_log.record(session_id, actor="system", action="erase", resource="session", purpose="rights")
        session_store.delete_session(session_id)   # temporary data cleared after submit
        result["cleared"] = True
    return result


@router.post("/{session_id}/route")
def route_record(session_id: str, body: RouteRequest) -> dict:
    """Generate and deliver the patient summary to selected configured systems."""
    session = _require(session_id)
    if not session.get("consent", {}).get("given"):
        raise HTTPException(status_code=403, detail="Consent is required before routing a patient record.")
    summary = summary_builder.build_summary(session)
    abha = (abha_service.get_abha_link(session_id) or {}).get("abha_id")
    bundle = fhir_builder.build_bundle(session, summary, abha_id=abha)
    routing = _route_bundle(session_id, session, bundle, body.targets)
    return {"session_id": session_id, "routing": routing, "fhir_bundle": bundle}


def _route_bundle(session_id: str, session: dict, bundle: dict, targets: list[str]) -> dict:
    permissions = session.get("permissions") or {}
    result = {}
    for target in ("his", "abdm"):
        if target not in targets:
            continue
        allowed = permissions.get("hospital_records", True) if target == "his" else permissions.get("abdm_share", False)
        if not allowed:
            result[target] = {"configured": False, "pushed": False, "status": "permission_required"}
            continue
        try:
            pushed = fhir_builder.push_to_his(bundle) if target == "his" else fhir_builder.push_to_abdm_sandbox(bundle)
            configured = bool(settings.HIS_FHIR_URL) if target == "his" else bool(settings.ABDM_SANDBOX_FHIR_URL and settings.ABHA_MODE == "sandbox")
            result[target] = {"configured": configured, "pushed": pushed, "status": "delivered" if pushed else "not_configured"}
        except RuntimeError as exc:
            audit_log.record(session_id, actor="system", role="system", action="FHIR_EXPORT", resource=target, success=False, purpose=f"{target}_share")
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    return result
