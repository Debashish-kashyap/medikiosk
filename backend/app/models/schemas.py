"""API request/response models = the contract between frontend and backend.

Frontend (frontend/src/api.js) mirrors these shapes. If you change a field here,
update api.js too. Responses are returned as plain dicts by the routers to stay
flexible during the hackathon; requests are validated by these models.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class CreateSessionRequest(BaseModel):
    language: str = "en"
    ayush_mode: bool = False


class ConsentRequest(BaseModel):
    given: bool = True
    abha_id: str | None = Field(default=None, min_length=1, description="ABHA number/address required for patient authentication before intake")
    otp: str | None = Field(default=None, min_length=4, repr=False, description="One-time verification code; never persisted")

    @model_validator(mode="after")
    def require_abha_identity_before_intake(self):
        if self.given and not self.abha_id:
            raise ValueError("ABHA ID is required before collecting health information.")
        if self.given and self.abha_id and not self.abha_id.strip():
            raise ValueError("ABHA ID is required before collecting health information.")
        if self.given and self.abha_id and not self.otp:
            raise ValueError("OTP is required when requesting ABHA linkage.")
        return self


class AnswerRequest(BaseModel):
    node_id: str
    # Exactly one of touch_value / text is expected.
    touch_value: Optional[Any] = None      # str | int | list[str] from a tap
    text: Optional[str] = None             # transcript from voice
    confidence: Optional[float] = None     # ASR/mapping confidence for voice
    confirmed: bool = False                # true after patient confirms a low-conf value


class ASRResponse(BaseModel):
    transcript: str
    confidence: float
    language: str


class PermissionsRequest(BaseModel):
    """Patient's per-purpose data-sharing consent (DPDP purpose limitation).

    Disabling every field is a valid consent-withdrawal signal.
    """
    treating_clinician: bool = True    # the doctor seeing you now
    hospital_records: bool = True      # store in this facility's record
    abdm_share: bool = False           # share to ABDM / other providers
    research_anonymised: bool = False  # anonymised secondary use
