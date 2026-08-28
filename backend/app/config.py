"""App configuration. Kept dependency-free (plain env vars) for demo reliability."""
from __future__ import annotations

import os


class Settings:
    APP_NAME = "MediKiosk API"
    VERSION = "0.1.0"
    # Comma-separated allowed origins; "*" for hackathon demo.
    CORS_ORIGINS = os.getenv("MEDIKIOSK_CORS", "*").split(",")
    # Whether a real LLM is wired in (see core/llm_mapper.py). Off by default.
    USE_LLM = os.getenv("MEDIKIOSK_LLM", "").lower() in {"1", "true", "openai", "on"}
    # ASR: unset/auto uses faster-whisper if installed, else stub. "stub" forces stub.
    ASR_MODE = os.getenv("MEDIKIOSK_ASR", "").strip().lower()
    # A urlsafe base64 Fernet key. Required before encrypting persisted PHI.
    ENCRYPTION_KEY = os.getenv("MEDIKIOSK_ENCRYPTION_KEY", "")
    # Explicitly marks this prototype ABHA adapter as a mock.
    ABHA_MODE = os.getenv("MEDIKIOSK_ABHA_MODE", "mock").strip().lower()
    # Supplied only after ABDM sandbox onboarding. Never commit these values.
    ABDM_SANDBOX_ABHA_LINK_URL = os.getenv("MEDIKIOSK_ABDM_SANDBOX_ABHA_LINK_URL", "")
    ABDM_SANDBOX_FHIR_URL = os.getenv("MEDIKIOSK_ABDM_SANDBOX_FHIR_URL", "")
    ABDM_CLIENT_ID = os.getenv("MEDIKIOSK_ABDM_CLIENT_ID", "")
    ABDM_CLIENT_SECRET = os.getenv("MEDIKIOSK_ABDM_CLIENT_SECRET", "")


settings = Settings()
