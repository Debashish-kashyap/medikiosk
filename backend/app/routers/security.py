"""Protected record, ABHA mock, and administrative audit APIs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..core import abha_service, fhir_builder, summary_builder
from ..security.audit import record_event
from ..security.rbac import actor_from_headers, has_permission, require_permission
from ..store import audit_log, session_store

router = APIRouter(prefix="/api", tags=["security"])


class AbhaLinkRequest(BaseModel):
    patient_id: str = Field(min_length=1)
    abha_id: str = Field(min_length=1)
    otp: str | None = Field(default=None, min_length=4, repr=False)


class RecordRequest(BaseModel):
    patient_id: str = Field(min_length=1)


def _session(patient_id: str) -> dict:
    session = session_store.get_session(patient_id)
    if not session:
        raise HTTPException(status_code=404, detail="Patient record not found.")
    return session


def _can_view(actor: dict[str, str], patient_id: str) -> bool:
    return has_permission(actor["role"], "view_patient_record") or (
        has_permission(actor["role"], "view_own_record") and actor["user_id"] == patient_id
    )


@router.post("/records")
def export_record(body: RecordRequest, actor: dict[str, str] = Depends(actor_from_headers)) -> dict:
    if not _can_view(actor, body.patient_id):
        record_event(body.patient_id, user_id=actor["user_id"], role=actor["role"], action="ACCESS_DENIED", resource_id="record", success=False, request_id=actor["request_id"])
        raise HTTPException(status_code=403, detail="Not authorized for this record.")
    session = _session(body.patient_id)
    link = abha_service.get_abha_link(body.patient_id)
    record_event(body.patient_id, user_id=actor["user_id"], role=actor["role"], action="CREATE_SUMMARY", resource_id=body.patient_id, success=True, request_id=actor["request_id"])
    return {"patient_id": body.patient_id, "fhir_bundle": fhir_builder.build_bundle(session, summary_builder.build_summary(session), (link or {}).get("abha_id"))}


@router.get("/records/{patient_id}")
def get_record(patient_id: str, actor: dict[str, str] = Depends(actor_from_headers)) -> dict:
    if not _can_view(actor, patient_id):
        record_event(patient_id, user_id=actor["user_id"], role=actor["role"], action="ACCESS_DENIED", resource_id="record", success=False, request_id=actor["request_id"])
        raise HTTPException(status_code=403, detail="Not authorized for this record.")
    session = _session(patient_id)
    record_event(patient_id, user_id=actor["user_id"], role=actor["role"], action="VIEW_PATIENT_RECORD", resource_id=patient_id, success=True, request_id=actor["request_id"])
    return {"patient_id": patient_id, "summary": summary_builder.build_summary(session)}


@router.post("/abha/link")
def link_abha(body: AbhaLinkRequest, actor: dict[str, str] = Depends(actor_from_headers)) -> dict:
    if not (has_permission(actor["role"], "update_record") or (actor["user_id"] == body.patient_id and has_permission(actor["role"], "link_own_abha"))):
        raise HTTPException(status_code=403, detail="Not authorized to link ABHA.")
    try:
        link = abha_service.link_abha(body.patient_id, body.abha_id, body.otp)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except RuntimeError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="ABHA verification is temporarily unavailable.")
    record_event(body.patient_id, user_id=actor["user_id"], role=actor["role"], action="ABHA_LINK", resource_id=body.patient_id, success=True, request_id=actor["request_id"], purpose="identity_linkage")
    return {"patient_id": link["patient_id"], "linked": True, "mode": "mock"}


@router.delete("/abha/{patient_id}")
def unlink_abha(patient_id: str, actor: dict[str, str] = Depends(actor_from_headers)) -> dict:
    if not (has_permission(actor["role"], "update_record") or (actor["user_id"] == patient_id and has_permission(actor["role"], "link_own_abha"))):
        raise HTTPException(status_code=403, detail="Not authorized to unlink ABHA.")
    if not abha_service.unlink_abha(patient_id):
        raise HTTPException(status_code=404, detail="ABHA link not found.")
    record_event(patient_id, user_id=actor["user_id"], role=actor["role"], action="ABHA_UNLINK", resource_id=patient_id, success=True, request_id=actor["request_id"], purpose="identity_linkage")
    return {"patient_id": patient_id, "unlinked": True, "mode": "mock"}


@router.get("/audit-logs")
def get_audit_logs(actor: dict[str, str] = Depends(require_permission("view_audit_logs"))) -> dict:
    entries = audit_log.all_logs()
    return {"count": len(entries), "entries": entries}
