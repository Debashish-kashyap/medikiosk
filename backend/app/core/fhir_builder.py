"""Module D — FHIR R4 bundle generation for ABDM/ABHA + HIS interoperability.

We emit plain dicts shaped as FHIR R4 resources (no heavy deps, easy to demo/inspect).
For production validation, the Data/Security lane can load these into the
`fhir.resources` library, or POST to the ABDM sandbox HIP endpoints.

Why this matters for judging: showing a VALID FHIR bundle proves HIS-agnostic
interoperability without needing live ABDM sandbox onboarding (too slow for 4 days).

Owned by the Data/Security lane.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx

from ..config import settings


def _uuid_ref() -> str:
    return f"urn:uuid:{uuid.uuid4()}"


def build_fhir_bundle(patient_data: dict) -> dict:
    """Build a FHIR R4-style collection from already-captured kiosk data only.

    ``patient_data`` may contain ``session``, ``summary`` and ``abha_id``. This
    deliberately does not manufacture demographics, diagnoses, or ABHA IDs.
    """
    session = patient_data.get("session", patient_data)
    summary = patient_data.get("summary", {})
    abha_id = patient_data.get("abha_id")
    now = datetime.now(timezone.utc).isoformat()
    answers = session.get("answers", {})

    patient_ref = _uuid_ref()
    patient = {
        "fullUrl": patient_ref,
        "resource": {
            "resourceType": "Patient",
            "id": patient_ref.split(":")[-1],
        },
    }
    if abha_id:
        patient["resource"]["identifier"] = [{"system": "https://healthid.abdm.gov.in", "value": abha_id}]

    entries = [patient]

    # Condition = chief complaint (as reported text, NOT a coded diagnosis).
    condition_ref = _uuid_ref()
    entries.append(
        {
            "fullUrl": condition_ref,
            "resource": {
                "resourceType": "Condition",
                "id": condition_ref.split(":")[-1],
                "clinicalStatus": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                            "code": "active",
                        }
                    ]
                },
                "category": [{"text": "Reported complaint (patient self-report)"}],
                "code": {"text": str(summary.get("chief_complaint", "Unspecified"))},
                "subject": {"reference": patient_ref},
                "recordedDate": now,
                "note": [{"text": summary.get("hpi", "")}],
            },
        }
    )

    # Observation for pain severity (if captured).
    if answers.get("cp_severity") is not None:
        obs_ref = _uuid_ref()
        entries.append(
            {
                "fullUrl": obs_ref,
                "resource": {
                    "resourceType": "Observation",
                    "id": obs_ref.split(":")[-1],
                    "status": "preliminary",
                    "code": {"text": "Pain severity (0-10 self-reported)"},
                    "subject": {"reference": patient_ref},
                    "valueInteger": answers["cp_severity"],
                    "effectiveDateTime": now,
                },
            }
        )

    # AllergyIntolerance if a drug allergy was reported.
    if answers.get("drug_allergy") == "yes":
        allergy_ref = _uuid_ref()
        entries.append(
            {
                "fullUrl": allergy_ref,
                "resource": {
                    "resourceType": "AllergyIntolerance",
                    "id": allergy_ref.split(":")[-1],
                    "category": ["medication"],
                    "criticality": "unable-to-assess",
                    "code": {"text": "Drug allergy reported (specifics to confirm)"},
                    "patient": {"reference": patient_ref},
                    "recordedDate": now,
                },
            }
        )

    # Flag resources for red flags -> Observations with high priority interpretation.
    for flag in summary.get("red_flags", []):
        flag_ref = _uuid_ref()
        entries.append(
            {
                "fullUrl": flag_ref,
                "resource": {
                    "resourceType": "Observation",
                    "id": flag_ref.split(":")[-1],
                    "status": "preliminary",
                    "category": [{"text": "red-flag-alert"}],
                    "code": {"text": flag["label"]},
                    "interpretation": [{"text": flag["priority"]}],
                    "subject": {"reference": patient_ref},
                    "note": [{"text": flag["action"]}],
                    "effectiveDateTime": now,
                },
            }
        )

    # Existing OCR metadata can be represented without asserting clinical validity.
    for document in session.get("documents", []):
        doc_ref = _uuid_ref()
        entries.append({
            "fullUrl": doc_ref,
            "resource": {
                "resourceType": "DocumentReference", "id": doc_ref.split(":")[-1],
                "status": "current", "subject": {"reference": patient_ref},
                "type": {"text": str(document.get("type", "clinical document"))},
                "date": document.get("date") or now,
                "description": "OCR-extracted document metadata (verification required)",
            },
        })
        investigations = document.get("entities", {}).get("investigations", [])
        if investigations:
            report_ref = _uuid_ref()
            entries.append({
                "fullUrl": report_ref,
                "resource": {
                    "resourceType": "DiagnosticReport", "id": report_ref.split(":")[-1],
                    "status": "preliminary", "subject": {"reference": patient_ref},
                    "effectiveDateTime": document.get("date") or now,
                    "code": {"text": "OCR-extracted investigations (verification required)"},
                    "conclusion": "; ".join(str(item.get("name", "")) for item in investigations),
                },
            })

    # Composition ties it into a physician-readable clinical summary document.
    composition_ref = _uuid_ref()
    entries.insert(
        1,
        {
            "fullUrl": composition_ref,
            "resource": {
                "resourceType": "Composition",
                "id": composition_ref.split(":")[-1],
                "status": "preliminary",
                "type": {"text": "Clinical history summary (pre-consultation)"},
                "subject": {"reference": patient_ref},
                "date": now,
                "title": "MediKiosk Pre-Consultation History",
                "section": [
                    {"title": "Chief complaint", "text": {"status": "generated", "div": str(summary.get("chief_complaint"))}},
                    {"title": "History of present illness", "text": {"status": "generated", "div": summary.get("hpi", "")}},
                    {"title": "Past medical history", "text": {"status": "generated", "div": summary.get("past_medical", "")}},
                    {"title": "Drug allergy", "text": {"status": "generated", "div": summary.get("drug_allergy", "")}},
                ],
            },
        },
    )

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": now,
        "meta": {"profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/DocumentBundle"]},
        "entry": entries,
    }


def build_bundle(session: dict, summary: dict, abha_id: str | None = None) -> dict:
    """Backward-compatible entry point used by the current session routers."""
    return build_fhir_bundle({"session": session, "summary": summary, "abha_id": abha_id})


def push_to_abdm_sandbox(bundle: dict) -> bool:
    """Send a generated bundle only to a configured ABDM sandbox endpoint.

    This is deliberately disabled unless sandbox mode, a destination URL, and
    onboarding credentials are configured. It never runs merely by building FHIR.
    """
    if settings.ABHA_MODE != "sandbox" or not settings.ABDM_SANDBOX_FHIR_URL:
        return False
    if not settings.ABDM_CLIENT_ID or not settings.ABDM_CLIENT_SECRET:
        raise RuntimeError("ABDM sandbox FHIR export is not configured.")
    try:
        response = httpx.post(
            settings.ABDM_SANDBOX_FHIR_URL,
            json=bundle,
            headers={"X-Client-Id": settings.ABDM_CLIENT_ID, "X-Client-Secret": settings.ABDM_CLIENT_SECRET},
            timeout=15.0,
        )
        response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        raise RuntimeError("ABDM sandbox FHIR export failed.") from exc
