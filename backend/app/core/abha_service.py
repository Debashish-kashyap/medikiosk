"""ABHA linkage seam: mock by default, sandbox only with supplied onboarding config.

OTP values are accepted only for the outbound verification request and are never
stored, returned, or added to audit events.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from ..config import settings

_LINKS: dict[str, dict[str, str]] = {}


def link_abha(patient_id: str, abha_id: str, otp: str | None = None) -> dict[str, str]:
    """Link after sandbox verification when enabled; otherwise use the labelled mock."""
    if not patient_id or not abha_id or not abha_id.strip():
        raise ValueError("patient_id and abha_id are required")
    if settings.ABHA_MODE == "sandbox":
        _verify_with_sandbox(abha_id.strip(), otp)
    elif settings.ABHA_MODE != "mock":
        raise RuntimeError("MEDIKIOSK_ABHA_MODE must be 'mock' or 'sandbox'.")
    _LINKS[patient_id] = {"patient_id": patient_id, "abha_id": abha_id.strip(), "linked_at": datetime.now(timezone.utc).isoformat()}
    return dict(_LINKS[patient_id])


def _verify_with_sandbox(abha_id: str, otp: str | None) -> None:
    """Call a provisioned ABDM sandbox adapter; exact URL comes from onboarding."""
    if not otp:
        raise ValueError("OTP is required for sandbox ABHA verification.")
    if not settings.ABDM_SANDBOX_ABHA_LINK_URL or not settings.ABDM_CLIENT_ID or not settings.ABDM_CLIENT_SECRET:
        raise RuntimeError("ABDM sandbox linkage is not configured.")
    try:
        response = httpx.post(
            settings.ABDM_SANDBOX_ABHA_LINK_URL,
            json={"abha_id": abha_id, "otp": otp},
            headers={"X-Client-Id": settings.ABDM_CLIENT_ID, "X-Client-Secret": settings.ABDM_CLIENT_SECRET},
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError("ABDM sandbox ABHA verification failed.") from exc


def unlink_abha(patient_id: str) -> bool:
    return _LINKS.pop(patient_id, None) is not None


def get_abha_link(patient_id: str) -> dict[str, str] | None:
    link = _LINKS.get(patient_id)
    return dict(link) if link else None
