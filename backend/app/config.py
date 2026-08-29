"""App configuration. Supports environment variables and .env file."""
from __future__ import annotations

import os
from pathlib import Path

# Load .env file if present
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass


class Settings:
    APP_NAME = "MediKiosk API"
    VERSION = "0.1.0"
    # Comma-separated allowed origins; "*" for hackathon demo.
    CORS_ORIGINS = os.getenv("MEDIKIOSK_CORS", "*").split(",")
    # Gemini API key (Google AI Studio free tier)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    # Gemini Model for Vision & NLU
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    # Whether a real LLM is wired in. Enabled if MEDIKIOSK_LLM is set OR if GEMINI_API_KEY is present.
    USE_LLM = os.getenv("MEDIKIOSK_LLM", "").lower() in {"1", "true", "gemini", "openai", "on"} or bool(GEMINI_API_KEY)
    # ASR: unset/auto uses faster-whisper if installed, else stub. "stub" forces stub.
    ASR_MODE = os.getenv("MEDIKIOSK_ASR", "").strip().lower()


settings = Settings()

