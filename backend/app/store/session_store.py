"""Durable SQLite session and patient-record store."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..config import settings

_SESSIONS: dict[str, dict] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    path = Path(settings.DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS patient_sessions (
            session_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.commit()
    return connection


def create_session(language: str = "en", ayush_mode: bool = False) -> dict:
    sid = uuid.uuid4().hex
    now = _now()
    session = {
        "id": sid,
        "language": language,
        "ayush_mode": bool(ayush_mode),
        "ayush_done": False,
        "current_node": None,
        "answers": {},
        "answer_meta": {},
        "red_flags": [],
        "consent": {"given": False, "ts": None, "identity_type": None},
        "permissions": {"treating_clinician": True, "hospital_records": True, "abdm_share": False, "research_anonymised": False},
        "physician_review": {"hpi": None, "edited_by": None, "edited_at": None, "confirmed": False, "confirmed_by": None, "confirmed_at": None},
        "queue_priority": None,
        "documents": [],
        "status": "in_progress",
        "created_at": now,
        "updated_at": now,
    }
    save_session(session)
    return session


def get_session(session_id: str) -> dict | None:
    if session_id in _SESSIONS:
        return _SESSIONS[session_id]
    with _connect() as connection:
        row = connection.execute(
            "SELECT payload FROM patient_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    if not row:
        return None
    session = json.loads(row["payload"])
    _SESSIONS[session_id] = session
    return session


def save_session(session: dict) -> dict:
    session["updated_at"] = _now()
    _SESSIONS[session["id"]] = session
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO patient_sessions (session_id, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                payload = excluded.payload, updated_at = excluded.updated_at
            """,
            (
                session["id"],
                json.dumps(session, ensure_ascii=False),
                session.get("created_at", session["updated_at"]),
                session["updated_at"],
            ),
        )
        connection.commit()
    return session


def delete_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)
    with _connect() as connection:
        connection.execute("DELETE FROM patient_sessions WHERE session_id = ?", (session_id,))
        connection.commit()


def all_sessions() -> dict[str, dict]:
    with _connect() as connection:
        rows = connection.execute("SELECT session_id, payload FROM patient_sessions").fetchall()
    for row in rows:
        _SESSIONS[row["session_id"]] = json.loads(row["payload"])
    return _SESSIONS
