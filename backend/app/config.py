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


settings = Settings()
