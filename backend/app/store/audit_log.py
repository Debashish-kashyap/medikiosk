"""Tamper-evident, append-only audit trail — the Estonia "visible access log" model.

Every read/write on a patient session is recorded as an entry that is *hash-chained*
to the one before it:  entry.hash = sha256(prev_hash + entry_body).  Editing or
removing any past entry breaks the chain, so tampering is detectable (`verify_chain`).

This is the in-memory demo store. Production swaps it for an append-only / WORM table
or ledger behind these same four functions — no caller changes needed.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

# session_id -> ordered list of audit entries
_LOG: dict[str, list[dict[str, Any]]] = {}

GENESIS = "0" * 64
_BODY_KEYS = ("seq", "ts", "actor", "role", "action", "resource", "purpose", "success", "request_id")


def _hash(prev_hash: str, body: dict[str, Any]) -> str:
    payload = prev_hash + json.dumps(body, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record(
    session_id: str,
    actor: str,
    action: str,
    resource: str,
    purpose: str = "care",
    role: str = "system",
    success: bool = True,
    request_id: str = "",
) -> dict[str, Any]:
    """Append one audit entry for a session and return it.

    actor    -- who acted: "patient", "clinician", "clinician:dr_rao", "system"
    action   -- what happened: "create", "view", "update", "export", "erase", "consent"
    resource -- what was touched: "session", "summary", "fhir_bundle", "access_log"
    purpose  -- why (DPDP purpose limitation): "care", "consent", "transparency", "rights"
    """
    chain = _LOG.setdefault(session_id, [])
    prev_hash = chain[-1]["hash"] if chain else GENESIS
    body = {
        "seq": len(chain),
        "ts": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "role": role,
        "action": action,
        "resource": resource,
        "purpose": purpose,
        "success": success,
        "request_id": request_id,
    }
    entry = {**body, "prev_hash": prev_hash, "hash": _hash(prev_hash, body)}
    chain.append(entry)
    return entry


def get_log(session_id: str) -> list[dict[str, Any]]:
    """Full audit trail for a session (oldest first)."""
    return list(_LOG.get(session_id, []))


def all_logs() -> list[dict[str, Any]]:
    """All technical audit entries, for the admin-only audit endpoint."""
    return [entry for chain in _LOG.values() for entry in chain]


def verify_chain(session_id: str) -> bool:
    """True if no past entry has been altered or removed (Estonia immutability)."""
    prev_hash = GENESIS
    for entry in _LOG.get(session_id, []):
        body = {k: entry.get(k) for k in _BODY_KEYS}
        if entry.get("prev_hash") != prev_hash or entry.get("hash") != _hash(prev_hash, body):
            return False
        prev_hash = entry["hash"]
    return True


def clear(session_id: str) -> None:
    """Drop a session's trail entirely.

    NOTE: the DPDP erasure path deliberately does NOT call this — it deletes the
    patient's *health data* but keeps the (health-data-free) audit trail so the
    erasure itself stays provable. Provided for a full-wipe option if you need it.
    """
    _LOG.pop(session_id, None)
