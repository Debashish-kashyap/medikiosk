"""ASR Benchmark Harness.

Run with: `pytest -m benchmark tests/test_benchmark_asr.py -v`
Skips automatically if faster-whisper is not installed.
"""
import math
import os
import tempfile
import wave
from typing import Generator

import pytest
from app.core.asr_engine import transcribe_audio, whisper_available

# Optional marker for slow benchmark tests
pytestmark = pytest.mark.benchmark


def _generate_sine_wave(file_path: str, duration_s: float = 1.0, freq: float = 440.0) -> None:
    """Generate a simple sine wave WAV file for testing without committing large audio binaries."""
    sample_rate = 16000
    num_samples = int(sample_rate * duration_s)
    
    with wave.open(file_path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            t = float(i) / sample_rate
            value = int(32767.0 * math.sin(2.0 * math.pi * freq * t))
            data = value.to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(data)


@pytest.fixture(scope="module")
def sample_audio_bytes() -> Generator[bytes, None, None]:
    """Provides a synthetic 1-second WAV file as bytes."""
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        _generate_sine_wave(path, duration_s=1.0)
        with open(path, "rb") as f:
            yield f.read()
    finally:
        os.unlink(path)


@pytest.mark.skipif(not whisper_available(), reason="faster-whisper not installed")
def test_benchmark_synthetic_audio(sample_audio_bytes: bytes):
    """Smoke test to ensure the transcription pipeline runs on valid audio."""
    # Since it's a sine wave, whisper might transcribe it as empty/hallucination 
    # (which gets filtered) or some random text. We just want to ensure it doesn't crash.
    result = transcribe_audio(sample_audio_bytes, language="en", content_type="audio/wav")
    
    assert result["engine"] == "faster-whisper"
    assert "transcript" in result
    assert isinstance(result["confidence"], float)
    assert result["duration_ms"] > 0
