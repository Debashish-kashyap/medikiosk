"""ASR seam tests. Never loads a Whisper model — the happy path stays keyless."""
from types import SimpleNamespace

from app.core import asr_engine
from app.core.asr_engine import _confidence_from_segments, transcribe_audio


def test_empty_audio_returns_contract():
    result = transcribe_audio(b"", "en")
    assert result["transcript"] == ""
    assert result["confidence"] == 0.0
    assert result["language"] == "en"
    assert "engine" in result


def test_confidence_from_segments():
    assert _confidence_from_segments([]) == 0.0
    segs = [
        SimpleNamespace(avg_logprob=-0.2, no_speech_prob=0.05),
        SimpleNamespace(avg_logprob=-0.4, no_speech_prob=0.1),
    ]
    conf = _confidence_from_segments(segs)
    assert 0.7 <= conf <= 1.0


def test_mock_text_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    res = client.post("/api/asr", data={"mock_text": "seene mein dard", "language": "hi"})
    assert res.status_code == 200
    body = res.json()
    assert body["transcript"] == "seene mein dard"
    assert body["confidence"] == 0.9
    assert body["language"] == "hi"
    assert body["engine"] == "mock"


def test_health_reports_asr_engine():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    body = client.get("/health").json()
    assert body["asr_engine"] in {"stub", "faster-whisper"}
    assert asr_engine.active_engine() == body["asr_engine"]
