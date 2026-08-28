"""Authenticated encryption for PHI that is persisted outside the transient session store.

Encrypt clinical documents, ABHA links, and stored exports at rest. Do not encrypt
non-sensitive indexes/audit metadata unnecessarily, and never log plaintext.
"""
from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings


def _fernet() -> Fernet:
    if not settings.ENCRYPTION_KEY:
        raise RuntimeError("MEDIKIOSK_ENCRYPTION_KEY is required for encryption.")
    try:
        return Fernet(settings.ENCRYPTION_KEY.encode("ascii"))
    except (ValueError, TypeError) as exc:
        raise RuntimeError("MEDIKIOSK_ENCRYPTION_KEY is not a valid Fernet key.") from exc


def encrypt_data(data: Any) -> str:
    """Serialize JSON-compatible data and return an authenticated ciphertext token."""
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _fernet().encrypt(raw).decode("ascii")


def decrypt_data(encrypted_data: str) -> Any:
    """Return the original JSON value; invalid/tampered ciphertext is rejected."""
    try:
        raw = _fernet().decrypt(encrypted_data.encode("ascii"))
        return json.loads(raw.decode("utf-8"))
    except InvalidToken as exc:
        raise ValueError("Encrypted data could not be authenticated.") from exc
