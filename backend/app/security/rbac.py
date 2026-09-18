"""Small, server-side role/permission policy for the prototype."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status

from .physician_auth import verify_token

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
    authorization: str | None = Header(default=None),
) -> dict[str, str]:
    """Demo identity seam. A real deployment verifies a JWT/ABHA identity here."""
    if authorization and authorization.startswith("Bearer "):
        token_actor = verify_token(authorization[7:].strip())
        if token_actor:
            return {**token_actor, "request_id": request.headers.get("X-Request-Id", "")}
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired physician token.")
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
