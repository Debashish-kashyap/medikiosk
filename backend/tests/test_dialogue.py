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


def test_ayush_mode_full_flow():
    # Session created with AYUSH mode enabled
    session = session_store.create_session(language="en", ayush_mode=True)
    q = dialogue_engine.current_question(session)
    assert q["node_id"] == "chief_complaint"

    # Cough branches to past_history in ontology, but with AYUSH mode routes to ayush_intro
    r_cc = _answer(session, "chief_complaint", touch_value="cough")
    assert r_cc["status"] == "accepted"
    assert r_cc["next_question"]["node_id"] == "ayush_intro"
    assert r_cc["next_question"]["type"] == "info_screen"
    assert "cta" in r_cc["next_question"]
    assert "skip_option" in r_cc["next_question"]

    # Start AYUSH intake
    r_intro = _answer(session, "ayush_intro", touch_value="start")
    assert r_intro["next_question"]["node_id"] == "ayush_prakriti"

    # Prakriti (body build)
    r_prakriti = _answer(session, "ayush_prakriti", touch_value="pitta_leaning")
    assert r_prakriti["next_question"]["node_id"] == "ayush_agni"

    # Agni (digestion)
    r_agni = _answer(session, "ayush_agni", touch_value="strong")
    assert r_agni["next_question"]["node_id"] == "ayush_sleep_bowel"
    assert r_agni["next_question"]["type"] == "multi_select"

    # Sleep & Bowel (multi-select)
    r_sb = _answer(session, "ayush_sleep_bowel", touch_value=["sleep_sound", "bowel_regular"])
    assert r_sb["next_question"]["node_id"] == "ayush_satmya"
    assert r_sb["next_question"]["type"] == "free_text"
    assert len(r_sb["next_question"]["quick_options"]) >= 4

    # Satmya (free text with quick chip)
    r_satmya = _answer(session, "ayush_satmya", touch_value="dairy")
    assert r_satmya["next_question"]["node_id"] == "ayush_satva"
    assert r_satmya["next_question"]["optional"] is True

    # Satva (stress / mental state)
    r_satva = _answer(session, "ayush_satva", touch_value="calm_steady")
    assert session["ayush_done"] is True
    # Now routes to past_history tail
    assert r_satva["next_question"]["node_id"] == "past_history"

    # Shared past_history tail
    r_past = _answer(session, "past_history", touch_value=["none"])
    assert r_past["next_question"]["node_id"] == "drug_allergy"

    r_end = _answer(session, "drug_allergy", touch_value="no")
    assert r_end["done"] is True
    assert session["status"] == "complete"

    # Verify summary builder incorporates ayush_profile
    from app.core import summary_builder
    summary = summary_builder.build_summary(session)
    assert summary["ayush_profile"] is not None
    assert "Medium build" in summary["ayush_profile"]["prakriti_cue"]
    assert "Strong" in summary["ayush_profile"]["ahara_shakti"]


def test_ayush_mode_skip_option():
    session = session_store.create_session(language="en", ayush_mode=True)
    dialogue_engine.current_question(session)

    r_cc = _answer(session, "chief_complaint", touch_value="cough")
    assert r_cc["next_question"]["node_id"] == "ayush_intro"

    # Patient chooses to skip AYUSH section
    r_skip = _answer(session, "ayush_intro", touch_value="skip")
    assert session["ayush_done"] is True
    assert r_skip["next_question"]["node_id"] == "past_history"


def test_phonetic_fallback_match():
    from app.core import summary_builder
    from app.core.llm_mapper import _match_candidate, _phonetic_match

    # Verify unit-level phonetic matching ("thane belt" vs "thin build")
    score = _phonetic_match("thin build", "thane belt")
    assert score >= 0.55
    assert _match_candidate("thin build", "thane belt") == score

    # End-to-end voice dialogue test: near-miss pronunciation resolves to valid option value
    # and summary pipeline renders canonical resolved label
    session = session_store.create_session(language="en", ayush_mode=True)
    dialogue_engine.current_question(session)
    _answer(session, "chief_complaint", touch_value="cough")
    _answer(session, "ayush_intro", touch_value="continue")

    # Spoken text "thane belt" phonetically resolves to vata_leaning
    r = _answer(session, "ayush_prakriti", text="thane belt")
    assert r["status"] == "accepted"
    assert r["stored"]["value"] == "vata_leaning"

    # Confirm the summary pipeline renders only the resolved, correctly-spelled label
    summary = summary_builder.build_summary(session)
    assert summary["ayush_profile"] is not None
    assert "Thin build" in summary["ayush_profile"]["prakriti_cue"]

