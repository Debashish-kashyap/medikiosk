"""API request/response models = the contract between frontend and backend.

Frontend (frontend/src/api.js) mirrors these shapes. If you change a field here,
update api.js too. Responses are returned as plain dicts by the routers to stay
flexible during the hackathon; requests are validated by these models.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class CreateSessionRequest(BaseModel):
    language: str = "en"
    ayush_mode: bool = False


class ConsentRequest(BaseModel):
    given: bool = True
    identity_type: Literal["abha", "aadhaar", "new_registration"] = "abha"
    identity_value: str | None = Field(default=None, min_length=1, description="ABHA ID or Aadhaar number")
    # Kept for clients using the original consent contract.
    abha_id: str | None = Field(default=None, min_length=1, description="Legacy alias for identity_value when identity_type is abha")
    full_name: str | None = Field(default=None, min_length=2)
    mobile_number: str | None = Field(default=None, min_length=10, max_length=15)
    otp: str | None = Field(default=None, min_length=4, repr=False, description="One-time verification code; never persisted")

    @model_validator(mode="after")
    def validate_identity_before_intake(self):
        if not self.given:
            return self

        if self.identity_type == "abha":
            self.identity_value = (self.identity_value or self.abha_id or "").strip()
            if not self.identity_value:
                raise ValueError("ABHA ID is required before collecting health information.")
        elif self.identity_type == "aadhaar":
            normalized = "".join(ch for ch in (self.identity_value or "") if ch.isdigit())
            if len(normalized) != 12:
                raise ValueError("Aadhaar number must contain 12 digits.")
            self.identity_value = normalized
        else:
            if not self.full_name or len(self.full_name.strip()) < 2:
                raise ValueError("Full name is required for new patient registration.")
            mobile = "".join(ch for ch in (self.mobile_number or "") if ch.isdigit())
            if len(mobile) < 10:
                raise ValueError("A valid mobile number is required for registration.")
            self.mobile_number = mobile[-10:]

        if not self.otp:
            raise ValueError("OTP is required to verify patient identity.")
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


class RouteRequest(BaseModel):
    targets: list[Literal["his", "abdm"]] = ["his"]


class PhysicianLoginRequest(BaseModel):
    user_id: str = Field(min_length=1)
    password: str = Field(min_length=1)


class PhysicianEditRequest(BaseModel):
    hpi: str = Field(min_length=1, max_length=20000)


class PriorityRequest(BaseModel):
    priority: Literal["critical", "review", "routine"]
