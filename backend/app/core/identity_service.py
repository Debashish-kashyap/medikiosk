"""Identity verification adapters for the patient intake boundary.

ABHA uses the existing sandbox adapter when configured. Aadhaar and new-patient
registration remain local verification seams until an authorised identity provider
is onboarded; sensitive values are reduced to a hash and last four digits.
"""
from __future__ import annotations

import hashlib
from typing import Any


def verify_local_identity(
    identity_type: str,
    identity_value: str | None = None,
    full_name: str | None = None,
    mobile_number: str | None = None,
) -> dict[str, Any]:
    """Return non-sensitive identity metadata for the temporary intake session."""
    value = (identity_value or mobile_number or "").strip()
    return {
        "identity_type": identity_type,
        "verified": True,
        "value_hash": hashlib.sha256(value.encode("utf-8")).hexdigest() if value else None,
        "value_last4": value[-4:] if value else None,
        "full_name": (full_name or "").strip() or None,
    }
