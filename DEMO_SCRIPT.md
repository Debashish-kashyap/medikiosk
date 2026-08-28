# MediKiosk — 90-second demo script

1. “This is MediKiosk: a consent-first clinical-intake assistant, not a diagnostic tool.”
2. Select Hindi or English and accept the privacy notice. “No health answer can be recorded
   before consent.”
3. Say “seene mein dard” or choose chest pain. Give the high-risk path: recent onset, central
   pressure, left-arm radiation, breathlessness, sweating. “The red flag is rule-based, not
   an LLM decision.”
4. Open the clinician summary. “The patient can review the captured information; raw audio is
   discarded after transcription.”
5. Generate the FHIR bundle. “Only captured data is mapped. An ABHA identifier is included
   only after linkage; sandbox sharing additionally requires explicit permission.”
6. Open the access log. “This is our Estonia-inspired differentiator: the patient can see the
   actor, role, time, purpose, and outcome for answers, uploads, exports, and access.”
7. Close: “For production we will complete ABDM onboarding, verified staff login, encrypted
   durable storage, key management, and clinical/legal validation.”
