"""Small signed-token authentication seam for the local physician workspace."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

_SECRET = os.getenv("MEDIKIOSK_AUTH_SECRET", "medikiosk-local-auth-change-me").encode("utf-8")
_DEFAULT_USER = os.getenv("MEDIKIOSK_PHYSICIAN_USER", "dr.mehta")
_DEFAULT_PASSWORD = os.getenv("MEDIKIOSK_PHYSICIAN_PASSWORD", "medikiosk-demo")


def authenticate(user_id: str, password: str) -> str | None:
    if not hmac.compare_digest(user_id, _DEFAULT_USER) or not hmac.compare_digest(password, _DEFAULT_PASSWORD):
        return None
    payload = {"user_id": user_id, "role": "physician", "exp": int(time.time()) + 8 * 60 * 60}
    encoded = _encode(payload)
    signature = hmac.new(_SECRET, encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_b64(signature)}"


def verify_token(token: str) -> dict[str, str] | None:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(_SECRET, encoded.encode("ascii"), hashlib.sha256).digest()
        if not hmac.compare_digest(signature, _b64(expected)):
            return None
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if int(payload.get("exp", 0)) < int(time.time()) or payload.get("role") != "physician":
            return None
        return {"user_id": str(payload["user_id"]), "role": "physician"}
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


def _encode(payload: dict) -> str:
    return _b64(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
