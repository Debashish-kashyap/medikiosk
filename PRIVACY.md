# MediKiosk — Patient Privacy & Data-Protection Design

Privacy-by-design for a patient-facing health kiosk, benchmarked against three references
the team chose: **Estonia** (health-data transparency), **Denmark / Sundhed.dk** (strong
national identity), and **India's DPDP Act 2023** (the law we must comply with).

> **TL;DR** — the patient can **see who accessed their record** (Estonia), every access is
> written to a **tamper-evident audit trail**, identity is anchored to **ABHA** (Denmark-style
> national ID), and the whole flow is **consent-first with DPDP data-principal rights**.

---

## 1. Principles (privacy-by-design)
- **Consent-first** — nothing is captured before explicit, informed consent.
- **Purpose limitation** — data is used only for the purposes the patient agreed to.
- **Data minimization** — only the structured fields the summary needs; raw audio is discarded after transcription.
- **Transparency** — the patient can see who touched their data, when, and why.
- **Storage limitation** — session data is wiped on submit (`?clear=true`) or by TTL.
- **Security** — TLS in transit, encryption at rest (prod), RBAC, and an immutable audit log.

---

## 2. Benchmark → what MediKiosk implements

| Reference | Their feature | MediKiosk implementation | Where | Status |
|---|---|---|---|---|
| 🇪🇪 Estonia | Patients see who accessed their records | Patient-visible **access log** — `GET /api/session/{id}/access-log` | `routers/privacy.py` | **Stub (works)** |
| 🇪🇪 Estonia | Every access creates an audit trail | Append-only, **hash-chained** entries; `verify_chain()` detects tampering | `store/audit_log.py` | **Stub (works)** |
| 🇪🇪 Estonia | Unauthorized access investigated/penalized | `tamper_evident` flag surfaced to patient; anomaly alerts + RBAC | `privacy.py` | Roadmap |
| 🇪🇪 Estonia | Citizens control sharing permissions | Per-purpose consent toggles — `POST /api/session/{id}/permissions` | `privacy.py`, `schemas.PermissionsRequest` | **Stub (works)** |
| 🇩🇰 Denmark | Strong national digital-identity auth | **ABHA** auth; actor identity recorded on every audit entry | `fhir_builder.py` (ABHA id) + auth seam | Partial |
| 🇮🇳 DPDP | Notice + explicit consent | Consent screen before any capture — `POST /api/session/{id}/consent` | `ConsentScreen.jsx`, `session.py` | **Real** |
| 🇮🇳 DPDP | Purpose limitation | Consent + permissions record the purpose per use | `privacy.py` | Stub |
| 🇮🇳 DPDP | Data-principal rights | `GET /rights`; access (`/summary`,`/fhir`), correct (edit HPI), erase (`DELETE /data`), withdraw (permissions off) | `privacy.py`, `SummaryView.jsx` | Mixed |
| 🇮🇳 DPDP | Data / storage minimization | Structured fields only; **audio discarded** after ASR; session wiped on submit | dialogue flow, `session_store`, `submit?clear` | Real (concept) |
| 🇮🇳 DPDP | Security safeguards | TLS, encryption at rest, RBAC, audit log | infra | Roadmap |

---

## 3. The tamper-evident audit trail (Estonia "immutable")
Each audit entry stores `hash = sha256(prev_hash + entry_body)`, chaining it to the entry
before it. Editing or deleting any past entry changes its hash, so the *next* entry's
`prev_hash` no longer matches — `verify_chain()` returns `False` and the tampering is
detectable. In-memory for the demo; production swaps in an append-only / WORM table or a
ledger behind the same four functions in `audit_log.py`.

Audit entries deliberately hold **no health data** — only `actor`, `action`, `resource`,
`purpose`, and `timestamp`. That is why the DPDP erasure path deletes the patient's health
data but *keeps* the audit trail: the erasure itself stays provable without retaining
anything sensitive.

---

## 4. Data lifecycle
```
consent  →  in-session structured fields  →  summary + FHIR export  →  submit
(explicit)   (audio transcribed, then           (physician reviews /       │
             discarded; only fields kept)         edits, then generates)    ▼
                                                          wipe now (?clear=true) or TTL expiry
```
Every step above writes an audit entry (create / consent / view / export / erase), so the
access log tells the full story of the record's life.

---

## 5. DPDP Act 2023 compliance checklist (for judges)
- [x] Notice + explicit consent before collection — `ConsentScreen`
- [x] Purpose limitation — consent + permissions record purpose
- [x] Data minimization — structured fields only; audio discarded
- [x] Transparency / access log — `GET /access-log`
- [x] Right to access — `GET /summary`, `GET /fhir`
- [x] Right to correction — edit HPI in `SummaryView`
- [x] Right to erasure — `DELETE /data`
- [x] Consent withdrawal — `POST /permissions` (all uses off)
- [ ] Storage limitation via enforced TTL — session TTL (roadmap: Redis TTL)
- [ ] Security safeguards — TLS + encryption at rest + RBAC (roadmap)
- [ ] Breach notification — audit-anomaly alerting (roadmap)
- [ ] ABDM Consent Manager artifact — align with ABHA consent (roadmap)

---

## 6. What's real vs. stub (be honest with judges)
| Real now | Stub / roadmap (seam in code) |
|---|---|
| Consent screen + consent record | Hash-chained trail is in-memory (→ WORM/DB) |
| Access-log, permissions, erasure, rights endpoints run | Actor identity is a label (→ real ABHA auth + RBAC) |
| Tamper-evidence (`verify_chain`) works | Breach-anomaly alerting |
| Audio-discard + structured-only capture | Enforced TTL, encryption at rest |
| DPDP rights map to real endpoints | ABDM Consent Manager integration |

---

## 7. Files
- `backend/app/store/audit_log.py` — hash-chained, append-only audit trail
- `backend/app/routers/privacy.py` — access-log, permissions, erasure, rights
- `backend/app/models/schemas.py` — `PermissionsRequest`
- `backend/app/routers/{session,summary}.py` — audit hooks on create / consent / view / export / erase
- `frontend/src/components/ConsentScreen.jsx` — notice + consent

## 8. Roadmap (post-hackathon)
Real ABHA authentication + staff RBAC and identity; DB-backed WORM audit store; breach
notification; ABDM Consent Manager consent artifacts; encryption at rest; a DPO / grievance
workflow. Wire `audit_log.record()` into every remaining router (`dialogue.py`,
`documents.py`) so the trail is exhaustive.
