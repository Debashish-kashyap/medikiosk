"""Patient privacy & DPDP data-principal rights (Module D).

Implements the benchmark features documented in ../../../PRIVACY.md:
  * Estonia   -- patient-visible access log backed by a tamper-evident audit trail.
  * Denmark   -- strong identity (ABHA) ties each actor to an audit entry.
  * India DPDP -- consent/permission control + rights (access, correct, erase, withdraw).

Storage is stubbed (in-memory), but the API shape is production-ready. Lane 6 owns
promoting these stubs to real (DB-backed trail, RBAC, ABHA auth, breach alerts).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..models.schemas import PermissionsRequest
from ..store import audit_log, session_store
from ..security.rbac import require_permission

router = APIRouter(prefix="/api/session", tags=["privacy"])


def _require(session_id: str) -> dict:
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or already cleared.")
    return session


def _humanize(entry: dict) -> dict:
    """Patient-facing view of one access: who, when, what, why."""
    return {
        "when": entry["ts"],
        "who": entry["actor"],
        "role": entry.get("role", "unknown"),
        "did": entry["action"],
        "to": entry["resource"],
        "why": entry["purpose"],
        "result": "success" if entry.get("success", True) else "denied/failed",
    }


@router.get("/{session_id}/access-log")
def access_log(session_id: str) -> dict:
    """Estonia model: let the patient see every access to their own record."""
    _require(session_id)
    # Viewing the log is itself an access — record it, then return the trail.
    audit_log.record(session_id, actor="patient", action="view", resource="access_log", purpose="transparency")
    entries = audit_log.get_log(session_id)
    return {
        "session_id": session_id,
        "tamper_evident": audit_log.verify_chain(session_id),
        "count": len(entries),
        "entries": [_humanize(e) for e in entries],
    }


@router.get("/{session_id}/audit")
def audit_trail(session_id: str, _actor: dict = Depends(require_permission("view_audit_logs"))) -> dict:
    """Full technical audit trail (RBAC-gated to staff in production)."""
    _require(session_id)
    return {
        "session_id": session_id,
        "chain_valid": audit_log.verify_chain(session_id),
        "entries": audit_log.get_log(session_id),
    }


@router.post("/{session_id}/permissions")
def set_permissions(session_id: str, body: PermissionsRequest) -> dict:
    """DPDP consent control: the patient toggles what their data may be used for."""
    session = _require(session_id)
    session["permissions"] = body.model_dump()
    session_store.save_session(session)
    audit_log.record(session_id, actor="patient", action="update", resource="permissions", purpose="consent")
    return {"session_id": session_id, "permissions": session["permissions"]}


@router.delete("/{session_id}/data")
def erase_data(session_id: str) -> dict:
    """DPDP right to erasure: delete health data; keep the audit of the erasure."""
    _require(session_id)
    audit_log.record(session_id, actor="patient", action="erase", resource="session", purpose="rights")
    session_store.delete_session(session_id)
    return {
        "session_id": session_id,
        "erased": True,
        "note": "Health data deleted. The tamper-evident audit trail of the erasure is "
                "retained (it holds no health data) so the erasure itself stays provable.",
    }


@router.get("/{session_id}/rights")
def data_principal_rights(session_id: str) -> dict:
    """DPDP Act 2023 rights available to this patient, with where to exercise each."""
    _require(session_id)
    return {
        "session_id": session_id,
        "rights": {
            "access": "GET /api/session/{id}/summary and /fhir — export your record",
            "correction": "edit the summary / HPI before it is finalised",
            "erasure": "DELETE /api/session/{id}/data",
            "consent_withdrawal": "POST /api/session/{id}/permissions with all uses disabled",
            "transparency": "GET /api/session/{id}/access-log — see who accessed your data",
        },
        "grievance_contact": "dpo@medikiosk.example (stub)",
    }
