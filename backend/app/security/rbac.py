"""Small, server-side role/permission policy for the prototype."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status

ROLE_PERMISSIONS = {
    "patient": {"view_own_record", "create_own_record", "withdraw_consent", "link_own_abha"},
    "physician": {"view_patient_record", "create_summary", "update_record"},
    "admin": {"manage_users", "view_audit_logs"},
}


def has_permission(role: str | None, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get((role or "").lower(), set())


def actor_from_headers(
    request: Request,
    x_user_id: str | None = Header(default=None),
    x_role: str | None = Header(default=None),
) -> dict[str, str]:
    """Demo identity seam. A real deployment verifies a JWT/ABHA identity here."""
    if not x_user_id or not x_role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    role = x_role.lower()
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown role.")
    return {"user_id": x_user_id, "role": role, "request_id": request.headers.get("X-Request-Id", "")}


def require_permission(permission: str):
    def dependency(actor: dict[str, str] = Depends(actor_from_headers)) -> dict[str, str]:
        if not has_permission(actor["role"], permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this action.")
        return actor
    return dependency
