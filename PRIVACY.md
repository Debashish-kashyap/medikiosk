# MediKiosk — Privacy & Data-Protection Design

This prototype demonstrates privacy-by-design controls for a patient-facing healthcare
kiosk. It supports DPDP principles; it is not a legal-compliance certification.

## Principles

- Consent before health-data collection.
- Purpose limitation through per-purpose permissions.
- Data minimisation: structured answers only; raw audio is discarded after transcription.
- Patient transparency through a visible access log.
- Secure handling through RBAC, authenticated-encryption utilities, and auditability.
- Erasure support and a documented production retention roadmap.

## Estonia differentiator: patient-visible access log

`GET /api/session/{session_id}/access-log` returns a patient-friendly view of each relevant
event: time, pseudonymous actor, role, action, resource, purpose, and result. It is supported
by an append-only, SHA-256 hash-chained trail in `store/audit_log.py`.

The following current flows record events: session creation, consent, questionnaire answer or
confirmation request, denied pre-consent collection, document upload, summary/FHIR view and
export, permission change, access-log view, and erasure. Audit events never contain clinical
content, passwords, access tokens, raw audio, ABHA numbers, or OTPs.

## ABHA and ABDM sandbox boundary

Consent may include an ABHA identifier and a one-time OTP. The OTP is transient: it is used
only for a configured sandbox verification call and is never persisted, returned, or audited.
Default mode is clearly labelled `mock`. Sandbox mode requires sanctioned ABDM onboarding and
the environment variables in `.env.example`; no code path claims a live integration without
that configuration.

A generated FHIR bundle includes an ABHA identifier only after successful linkage. Export to a
configured sandbox requires the separate `abdm_share` purpose permission.

## DPDP demonstration checklist

- [x] Notice and explicit consent before questionnaire/document collection.
- [x] Purpose limitation through consent and sharing permissions.
- [x] Data minimisation: structured fields; raw audio discarded after ASR.
- [x] Transparency: patient-visible access log.
- [x] Access: summary and FHIR export endpoints.
- [x] Correction: clinician/patient summary review flow.
- [x] Erasure: `DELETE /api/session/{id}/data` deletes session health data while retaining
  health-data-free audit evidence.
- [x] Withdrawal: permissions can be disabled.
- [x] Application controls: server-side RBAC, audit trail, and authenticated encryption utility.
- [ ] Production controls: TLS, encrypted database/backups, KMS key rotation, TTL retention,
  breach response, verified staff identity, and DPO/grievance workflow.
- [ ] ABDM Consent Manager artifacts and production legal/clinical validation.

## Current status and production roadmap

The demo's session and audit stores are in-memory. Production should replace them with a
durable encrypted store with retention rules and an append-only/WORM audit trail. Replace demo
identity headers with verified staff and patient identity claims, complete ABDM sandbox
onboarding, use least-privilege service credentials, and add monitoring and breach response.
