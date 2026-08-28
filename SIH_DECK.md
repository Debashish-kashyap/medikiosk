# MediKiosk — 6-slide SIH deck

## 1. The problem: the first 10 minutes are unsafe and inefficient

Patients repeat their history, clinicians receive unstructured information, and red flags can
be missed before the consultation. Rural and multilingual settings make this worse.

**MediKiosk:** a voice + touch pre-consultation kiosk that converts verified patient answers
into a clinician-ready summary — never a diagnosis.

## 2. Our solution: controlled clinical intake

`Consent → voice/touch → structured fields → confidence check → red-flag rules → summary → FHIR`

The dialogue graph decides what is asked next. The LLM, when enabled, only maps speech to
allowed values. Low-confidence speech is confirmed; the system never invents medical facts.

## 3. Safety and usability by design

- Hindi/English voice and touch fallback
- Deterministic branching and rule-based red flags
- Uploaded records become structured, clearly marked OCR extracts
- Clinician review occurs before any external sharing

**Demo moment:** chest pain + breathlessness + sweating immediately raises a high-priority alert.

## 4. Interoperability: FHIR + ABHA-ready architecture

FHIR R4-style bundle maps captured data only: Patient, Condition, Observation,
DiagnosticReport, and DocumentReference. ABHA linkage is mock by default; a sandbox adapter
activates only with authorised configuration and explicit sharing consent.

## 5. Privacy differentiator: visible, accountable care

Consent precedes collection. Every key interaction is appended to a tamper-evident audit trail.
The patient can see who accessed what, when, why, and whether it succeeded. OTPs, passwords,
tokens, raw audio, and clinical payloads are never placed in the audit log.

## 6. Feasible today, production-ready next

**Working demo:** controlled intake, red-flag detection, summary, FHIR export, consent,
patient-visible audit log, RBAC seam, and encrypted-data utility.

**Next:** verified identity, ABDM onboarding, encrypted durable storage with retention, KMS,
WORM audit storage, DPIA/legal review, and clinical validation.
