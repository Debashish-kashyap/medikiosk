# Contributing to MediKiosk

A 4-day, 6-person SIH build. This file tells each member where their lane is and gives
them 3 starter tickets. Read the [README](./README.md) for setup and the
[plan doc](../MediKiosk%20-%20SIH%20Approach%20%26%20Feasibility%20Plan.md) for strategy.

## Ground rules
- **Develop locally, not in Docker** (hot reload) — see README. Docker is demo-only.
- **Freeze the API contract on Day 1** — `backend/app/models/schemas.py` + `frontend/src/api.js`. Everyone builds against it; changes to it go through the Lane-3 integrator.
- **Keep the demo keyless at all times** — never commit code that *requires* an API key to run the happy path (real models go behind the `MEDIKIOSK_LLM` / `USE_LLM` seam).
- **Backend PRs must keep `pytest -q` green.**
- **No secrets in git** — `.env` is gitignored; use `.env.example` as the template.

## Branch, commit & PR conventions
- Branch: `lane<N>-<short>` — e.g. `lane4-asr-whisper`, `lane1-consent-a11y`.
- Commit: `[lane<N>] <imperative summary>` — e.g. `[lane5] add tesseract OCR for printed labs`.
- Open a PR into `main`; **never push to `main` directly**. Contract/`core/` changes need a Lane-3 review.
- Keep PRs small and demoable.

## Definition of done (per PR)
1. The demo happy-path still runs (local **or** `docker compose up`).
2. Backend: `pytest -q` passes.
3. No secrets committed.
4. If you promoted a stub to real, update the **"real vs stubbed"** table in the README (and `PRIVACY.md` if it's a privacy feature).

---

## The 6 lanes — owner, files, first tickets
Tickets go T1 (quick win, do first) → T3 (stretch). Pick up your lane and start at T1.

### Lane 1 — Frontend / Kiosk UX
**Files:** `components/{LanguageSelect,ConsentScreen,QuestionCard,VoiceButton}.jsx`, `i18n.js`, `index.css`
- **T1:** Make every tap target ≥64 px, high-contrast, with a large-font toggle and a clear "🔊 repeat question" button (accessibility for elderly / low-literacy patients).
- **T2:** Add a third language to `i18n.js` + `SPEECH_LANG` (e.g. Marathi or Tamil) and verify both voice and touch paths.
- **T3:** Add a progress indicator and Back / Repeat navigation across the interview.

### Lane 2 — Frontend / Physician & Docs UI
**Files:** `components/{SummaryView,RedFlagBanner}.jsx`, `App.jsx`, `api.js`
- **T1:** Polish `SummaryView` into a clean, print-friendly physician card (clear sections, edit-in-place HPI).
- **T2:** Make `RedFlagBanner` impossible to miss (color, icon, sticky) with an "acknowledge" action.
- **T3:** Build the **patient access-log screen** — call `GET /api/session/{id}/access-log`, show "who accessed your data, when, and why" + the `tamper_evident` badge (pairs with Lane 6).

### Lane 3 — Backend Lead / Integrator
**Files:** `core/{dialogue_engine,ontology_loader,validation}.py`, `routers/`, `store/session_store.py`, `models/schemas.py`
- **T1:** **FREEZE the API contract** (schemas.py + api.js) and post it in the team channel — this is a Day-1 blocker for everyone else.
- **T2:** Add one more chief complaint to `clinical_ontology.json` end-to-end (e.g. cough/breathlessness) and keep `pytest` green — proves the engine is data-driven.
- **T3:** Swap `session_store` to Redis + TTL behind the same interface (storage-limitation for privacy).

### Lane 4 — AI / Speech (ASR)
**Files:** `routers/asr.py`, `components/VoiceButton.jsx`
- **T1:** Wire real ASR behind `POST /api/asr` (faster-whisper locally, or Bhashini/AI4Bharat), returning `transcript` + `confidence`; keep the browser Web Speech fallback.
- **T2:** Add basic noise handling / VAD and tune the confidence threshold against the gate in `validation.py`.
- **T3:** Benchmark word-accuracy on 5 noisy Hindi/English clips and document the numbers for the judges.

### Lane 5 — AI / NLU, OCR & Summary
**Files:** `core/{llm_mapper,summary_builder}.py`, `routers/documents.py`
- **T1:** Replace the `documents.py` stub with real OCR (Tesseract / PaddleOCR) for **printed** prescriptions & labs; extract key fields and flag out-of-range values.
- **T2:** Improve HPI phrasing in `llm_mapper.phrase_hpi` (template-first; optional real LLM behind `USE_LLM`).
- **T3:** With Lane 3, expand the red-flag rules in `clinical_ontology.json` and add tests.

### Lane 6 — Data / Security / Presentation
**Files:** `core/fhir_builder.py`, `store/audit_log.py`, `routers/privacy.py`, `PRIVACY.md`, pitch deck
- **T1:** Complete the **patient-visible access log** (the Estonia differentiator): sprinkle `audit_log.record()` into `dialogue.py` and `documents.py` so the trail is exhaustive, and support Lane 2's access-log screen. See [`PRIVACY.md`](./PRIVACY.md).
- **T2:** ABHA auth — capture ABHA + OTP at consent, attach the real actor identity to audit entries, and wire real ABDM-sandbox linkage in `fhir_builder`.
- **T3:** Own the **6-slide SIH deck** + demo script, and complete the DPDP compliance checklist in `PRIVACY.md`.

---

## Where the deep docs live
- **Strategy / feasibility / 21-judge-question playbook:** `../MediKiosk - SIH Approach & Feasibility Plan.md`
- **Privacy design + DPDP checklist:** [`PRIVACY.md`](./PRIVACY.md)
- **Live API contract:** http://localhost:8000/docs
