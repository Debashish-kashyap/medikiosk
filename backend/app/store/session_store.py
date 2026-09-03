"""In-memory session store.

For the hackathon demo this keeps sessions in a process dict, which is enough for
a single-kiosk demo AND satisfies "session data cleared after submit" (we just delete).

PRODUCTION (Data/Security lane): swap this for Redis with a TTL so temporary session
data auto-expires and the kiosk can run stateless behind a load balancer:
    redis.setex(f"session:{id}", ttl_seconds, json.dumps(session))
The public functions below (create/get/save/delete) are the seam to replace.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

_SESSIONS: dict[str, dict] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session(language: str = "en", ayush_mode: bool = False) -> dict:
    sid = uuid.uuid4().hex
    session = {
        "id": sid,
        "language": language,
        "ayush_mode": bool(ayush_mode),
        "ayush_done": False,
        "current_node": None,          # set to entry on first /next
        "answers": {},                 # field -> value (str | list | int)
        "answer_meta": {},             # field -> {source, confidence, transcript}
        "red_flags": [],               # list of fired flag dicts
        "consent": {"given": False, "ts": None},
        "documents": [],               # OCR-extracted docs (Module B)
        "status": "in_progress",       # in_progress | complete
        "created_at": _now(),
        "updated_at": _now(),
    }
    _SESSIONS[sid] = session
    return session


def get_session(session_id: str) -> dict | None:
    return _SESSIONS.get(session_id)


def save_session(session: dict) -> dict:
    session["updated_at"] = _now()
    _SESSIONS[session["id"]] = session
    return session


def delete_session(session_id: str) -> None:
    """Clear temporary session data (privacy: called after submit)."""
    _SESSIONS.pop(session_id, None)


def all_sessions() -> dict[str, dict]:
    return _SESSIONS
