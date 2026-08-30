from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core import abha_service, fhir_builder
from app.security import encryption
from app.security.rbac import has_permission
from app.store import audit_log, session_store


def test_fhir_bundle_maps_only_captured_data():
    session = session_store.create_session()
    session["answers"]["cp_severity"] = 7
    bundle = fhir_builder.build_fhir_bundle({"session": session, "summary": {"chief_complaint": "chest pain", "hpi": "reported", "red_flags": []}})
    resources = [entry["resource"] for entry in bundle["entry"]]
    assert bundle["resourceType"] == "Bundle"
    assert not resources[0].get("identifier")  # no invented ABHA identifier
    assert any(resource["resourceType"] == "Observation" for resource in resources)


def test_rbac_permissions():
    assert has_permission("patient", "view_own_record")
    assert has_permission("physician", "update_record")
    assert has_permission("admin", "view_audit_logs")
    assert not has_permission("patient", "view_audit_logs")


def test_encryption_round_trip_and_tamper_rejection(monkeypatch):
    monkeypatch.setattr(encryption.settings, "ENCRYPTION_KEY", Fernet.generate_key().decode())
    token = encryption.encrypt_data({"only": "minimum data"})
    assert encryption.decrypt_data(token) == {"only": "minimum data"}
    try:
        encryption.decrypt_data(token[:-2] + "aa")
    except ValueError:
        pass
    else:
        raise AssertionError("tampered ciphertext must be rejected")


def test_abha_mock_link_and_unlink():
    assert abha_service.link_abha("p1", "91-1234-5678-9012")["patient_id"] == "p1"
    assert abha_service.get_abha_link("p1") is not None
    assert abha_service.unlink_abha("p1") is True
    assert abha_service.get_abha_link("p1") is None


def test_consent_and_protected_record_api():
    from app.main import app

    client = TestClient(app)
    created = client.post("/api/session", json={"language": "en"}).json()
    patient_id = created["session_id"]
    # Health answers cannot be collected before consent or patient authentication.
    denied = client.post(f"/api/session/{patient_id}/answer", json={"node_id": "chief_complaint", "touch_value": "chest_pain"})
    assert denied.status_code == 403
    missing_abha = client.post(f"/api/session/{patient_id}/consent", json={"given": True, "otp": "123456"})
    assert missing_abha.status_code == 422
    consented = client.post(
        f"/api/session/{patient_id}/consent",
        json={"given": True, "abha_id": "91-1234-5678-9012", "otp": "123456"},
    )
    assert consented.status_code == 200
    answered = client.post(f"/api/session/{patient_id}/answer", json={"node_id": "chief_complaint", "touch_value": "chest_pain"})
    assert answered.status_code == 200
    visible_log = client.get(f"/api/session/{patient_id}/access-log")
    assert visible_log.status_code == 200
    assert any(entry["did"] == "UPDATE_PATIENT_RECORD" and entry["role"] == "patient" for entry in visible_log.json()["entries"])
    assert client.get(f"/api/records/{patient_id}").status_code == 401
    own = client.get(f"/api/records/{patient_id}", headers={"X-User-Id": patient_id, "X-Role": "patient"})
    assert own.status_code == 200
    staff = client.post("/api/records", json={"patient_id": patient_id}, headers={"X-User-Id": "dr-1", "X-Role": "physician"})
    assert staff.status_code == 200
    assert staff.json()["fhir_bundle"]["resourceType"] == "Bundle"
    assert client.get("/api/audit-logs", headers={"X-User-Id": "p", "X-Role": "patient"}).status_code == 403
    assert client.get("/api/audit-logs", headers={"X-User-Id": "admin", "X-Role": "admin"}).status_code == 200
    assert audit_log.verify_chain(patient_id)


def test_consent_abha_otp_is_not_returned_or_audited():
    from app.main import app

    client = TestClient(app)
    patient_id = client.post("/api/session", json={}).json()["session_id"]
    response = client.post(
        f"/api/session/{patient_id}/consent",
        json={"given": True, "abha_id": "91-1234-5678-9012", "otp": "123456"},
    )
    assert response.status_code == 200
    assert response.json()["consent"]["abha_linked"] is True
    assert "otp" not in response.text.lower()
    assert "123456" not in str(audit_log.get_log(patient_id))
