# MediKiosk — AI Clinical History Kiosk (SIH PS 26047)

Patient-facing kiosk that takes a medical history by **voice + touch**, digitizes prior
documents, runs a **rule-based red-flag** safety check, and produces an **editable,
physician-ready summary** + a **FHIR R4 bundle** for ABDM/ABHA — all before the consult.

> **Core principle:** the **LLM is not the source of truth**. Flow is
> `speech → ASR → structured fields → validation → summary`, driven by a deterministic
> **Dialogue State Machine + Clinical Ontology**. The LLM only maps speech to predefined
> values and phrases summaries. Emergencies are decided by **rules**, not the model.

Full strategy, 4-day plan, feasibility, and the 21-judge-question playbook are in
`../MediKiosk - SIH Approach & Feasibility Plan.md`.

---

## Quickstart

> **For the 4-day build, develop locally (below).** Docker is optional — it's for the demo
> laptop and one-command onboarding, and it rebuilds on every code change, so it is *not*
> meant for active development.

### Develop locally — recommended (two terminals, hot reload)
**Backend**
```bash
cd backend
python -m venv .venv
.\.venv/Scripts/activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000            # http://localhost:8000/docs
python -m pytest -q # optional: walks the clinical, security, and API checks
```
**Frontend**
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

It runs **with no API keys** — speech→field mapping uses an offline alias matcher, and
ASR uses the browser’s built-in Web Speech API. Plug real models in later (see lanes).

**Lane 4 (optional local Whisper):** `pip install faster-whisper`, install ffmpeg, set
`MEDIKIOSK_ASR=whisper`. The kiosk still uses Web Speech unless you also set
`VITE_USE_SERVER_ASR=1` (then mic audio is POSTed to `/api/asr`).

### Docker — optional (demo machine / one-command run)
```bash
docker compose up --build          # Kiosk UI → :5173   API docs → :8000/docs
```
One command, no local Python/Node needed. No source hot-reload, though — rebuild to see
code changes, so use the local flow above while building.

---

## Try the demo (90 seconds)
1. Choose language → accept consent.
2. “What brings you in today?” → **speak** “seene mein dard” / “chest pain”, or tap.
3. Answer the SOCRATES follow-ups. Say something garbled once → the kiosk asks you to
   **repeat or tap** (confidence gate).
4. Say **yes** to breathlessness **and** sweating → **RED-FLAG banner** appears.
5. On the summary screen, **upload any file** → a stubbed prescription/lab extraction
   appears with an out-of-range value flagged.
6. Edit the HPI line, then **Finish & generate record** → a valid **FHIR bundle** prints.

---

## Repo structure
```
medikiosk/
├── docker-compose.yml
├── backend/                     # FastAPI + deterministic engine
│   ├── app/
│   │   ├── main.py              # app + routers + /health
│   │   ├── config.py
│   │   ├── data/clinical_ontology.json   # ★ the dialogue graph + red-flag rules
│   │   ├── core/
│   │   │   ├── dialogue_engine.py        # ★ deterministic state machine
│   │   │   ├── ontology_loader.py
│   │   │   ├── red_flags.py              # ★ rule-based safety layer (not the LLM)
│   │   │   ├── validation.py             # confidence gate + contradiction checks
│   │   │   ├── llm_mapper.py             # bounded LLM (offline fallback)
│   │   │   ├── summary_builder.py        # Module C
│   │   │   └── fhir_builder.py           # Module D (FHIR R4)
│   │   ├── routers/             # session, dialogue, asr, documents, summary
│   │   ├── models/schemas.py    # API contract
│   │   └── store/session_store.py        # in-memory now; swap for Redis+TTL
│   └── tests/test_dialogue.py
└── frontend/                    # React (Vite) touch kiosk
    └── src/
        ├── App.jsx              # phase machine: language→consent→interview→summary
        ├── api.js               # mirrors backend contract
        ├── i18n.js              # UI strings (en/hi) + speech lang tags
        └── components/          # LanguageSelect, ConsentScreen, QuestionCard,
                                 # VoiceButton, RedFlagBanner, SummaryView
```

---

## API contract (see http://localhost:8000/docs)
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/session` | Create session, returns first question |
| POST | `/api/session/{id}/consent` | Record consent |
| GET  | `/api/session/{id}/next` | Current question |
| POST | `/api/session/{id}/answer` | Submit voice/touch answer → next question / confirm / red flags |
| POST | `/api/asr` | Speech-to-text (`mock_text` or audio). Stub by default; faster-whisper when `MEDIKIOSK_ASR=whisper` |
| POST | `/api/session/{id}/documents` | Upload doc → stubbed OCR extraction (Module B) |
| GET  | `/api/session/{id}/summary` | Structured physician summary (Module C) |
| POST | `/api/session/{id}/submit` | Generate FHIR bundle; `?clear=true` wipes session |
| POST | `/api/records` | Protected FHIR export for a patient session |
| GET | `/api/records/{id}` | Protected patient/physician summary view |
| POST | `/api/abha/link` | ABHA linkage: mock by default; sandbox adapter only when authorised/configured |
| DELETE | `/api/abha/{id}` | Remove a mock ABHA link |
| GET | `/api/audit-logs` | Admin-only technical audit events |

Protected record endpoints use `X-User-Id` and `X-Role` (`patient`, `physician`, or
`admin`) as a **demo identity seam**. Replace these headers with verified identity/JWT
claims before deployment. Copy `.env.example` to `.env` and set a real
`MEDIKIOSK_ENCRYPTION_KEY` before encrypting persisted PHI; `.env` is gitignored.

**Answer payload:** `{ node_id, touch_value? , text?, confidence?, confirmed? }`
Low-confidence voice → `{status:"needs_confirmation", ...}`; the kiosk confirms or offers taps.

---

## Who owns what (6 lanes)
1. **Frontend — Kiosk UX:** `components/LanguageSelect`, `ConsentScreen`, `QuestionCard`, `VoiceButton`, `i18n.js` (accessibility, dual input, add languages).
2. **Frontend — Physician & Docs UI:** `SummaryView`, `RedFlagBanner`, upload UX, polish.
3. **Backend Lead / Integrator:** `dialogue_engine.py`, `ontology_loader.py`, `validation.py`, `routers/`, API contract, `session_store` → Redis.
4. **AI — Speech:** `routers/asr.py` + `VoiceButton` production path — faster-whisper / Bhashini, noise suppression, VAD, confidence.
5. **AI — NLU / OCR / Summary:** `llm_mapper.py`, `summary_builder.py`, `routers/documents.py` (real OCR + entity extraction), red-flag rules.
6. **Data / Security / Presentation:** `fhir_builder.py`, ABHA linkage, RBAC + audit log, encryption, DPDP story, **pitch deck + demo script**.

---

## What’s real vs. stubbed (be honest with judges)
| Real now | Stubbed (production seam marked in code) |
|---|---|
| Deterministic dialogue engine + branching | Real LLM mapping (offline alias matcher stands in) |
| Rule-based red-flag detection | OCR + entity extraction (`documents.py` returns samples) |
| Confidence gate + confirm/repeat loop | Live ABDM sandbox export requires sanctioned endpoint, credentials, and sharing consent; otherwise no request is made |
| Structured summary + editable HPI, consent-gated audit trail/RBAC seams | Redis TTL, durable encrypted storage, and WORM audit persistence |
| Valid FHIR R4 bundle generation | Handwriting OCR (printed only; handwriting = roadmap) |
| Voice via browser Web Speech API | Bhashini cloud ASR (optional; local faster-whisper is the Lane 4 seam) |
| `POST /api/asr` + MediaRecorder fallback | faster-whisper until `MEDIKIOSK_ASR=whisper` + `pip install faster-whisper` |

---

## Extend the ontology (add a complaint)
Edit `backend/app/data/clinical_ontology.json`:
1. Add an option to `chief_complaint` with a `next` pointing to your first node.
2. Add your nodes; each `next` eventually points to `past_history` (shared tail) or `END`.
3. Add `aliases` per option so voice mapping works offline.
4. Optionally add rules to `red_flags`.

No engine code changes needed — the machine is data-driven. Re-run `pytest` to keep it green.
