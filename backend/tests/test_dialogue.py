"""Smoke test for the deterministic dialogue engine + red-flag layer.

Run from backend/:  pytest -q
No API key or network needed (offline alias mapping). This is the test the
Backend Lead extends as new complaints are added to the ontology.
"""
from app.core import dialogue_engine
from app.store import session_store


def _answer(session, node_id, touch_value=None, text=None, confidence=None, confirmed=False):
    return dialogue_engine.process_answer(
        session, node_id, touch_value=touch_value, text=text,
        confidence=confidence, confirmed=confirmed,
    )


def test_chest_pain_path_fires_acs_red_flag():
    session = session_store.create_session(language="en")
    q = dialogue_engine.current_question(session)
    assert q["node_id"] == "chief_complaint"

    # Voice answer maps "seene mein dard" -> chest_pain via aliases (no LLM key needed).
    r = _answer(session, "chief_complaint", text="seene mein dard")
    assert r["status"] == "accepted"
    assert session["answers"]["chief_complaint"] == "chest_pain"
    assert r["next_question"]["node_id"] == "cp_onset"

    # Walk the SOCRATES branch by touch.
    _answer(session, "cp_onset", touch_value="under_1h")
    _answer(session, "cp_site", touch_value="center")
    _answer(session, "cp_character", touch_value="pressure")
    _answer(session, "cp_radiation", touch_value="left_arm")   # should already flag radiation
    r_breath = _answer(session, "cp_breathless", touch_value="yes")
    r_sweat = _answer(session, "cp_sweating", touch_value="yes")

    flag_ids = {f["id"] for f in session["red_flags"]}
    assert "acs_classic" in flag_ids          # chest pain + breathless + sweating
    assert "acs_radiation" in flag_ids        # radiating to arm
    assert any(f["priority"] == "HIGH" for f in r_sweat["red_flags_all"])

    # Finish and confirm completion.
    _answer(session, "cp_severity", touch_value=8)
    _answer(session, "past_history", touch_value=["diabetes"])
    r_end = _answer(session, "drug_allergy", touch_value="no")
    assert r_end["done"] is True
    assert session["status"] == "complete"


def test_low_confidence_voice_requests_confirmation():
    session = session_store.create_session(language="en")
    dialogue_engine.current_question(session)
    # Gibberish -> no alias match -> low confidence -> must ask to confirm/repeat.
    r = _answer(session, "chief_complaint", text="mmmfff garbled noise", confidence=0.2)
    assert r["status"] == "needs_confirmation"
    assert "chief_complaint" not in session["answers"]
