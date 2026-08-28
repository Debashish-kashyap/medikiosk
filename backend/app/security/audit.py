"""Security-facing audit wrapper. Never send credentials or PHI to this module."""
from __future__ import annotations

from typing import Any

from ..store import audit_log


def record_event(session_id: str, *, user_id: str, role: str, action: str,
                 resource_id: str, success: bool, request_id: str = "", purpose: str = "care") -> dict[str, Any]:
    """Append a minimal event to the existing tamper-evident store."""
    return audit_log.record(
        session_id, actor=user_id, role=role, action=action, resource=resource_id,
        success=success, request_id=request_id, purpose=purpose,
    )
