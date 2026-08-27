"""MediKiosk FastAPI entrypoint.

Run (from the backend/ directory):
    uvicorn app.main:app --reload --port 8000
Interactive API docs at http://localhost:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .core.ontology_loader import load_ontology
from .routers import asr, dialogue, documents, privacy, session, summary

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session.router)
app.include_router(dialogue.router)
app.include_router(asr.router)
app.include_router(documents.router)
app.include_router(summary.router)
app.include_router(privacy.router)


@app.get("/health")
def health() -> dict:
    ont = load_ontology()
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "ontology_version": ont.version,
        "complaints": [o["value"] for o in ont.entry_node().get("options", [])],
        "llm_enabled": settings.USE_LLM,
    }
