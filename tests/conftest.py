"""Pytest configuration and shared fixtures."""
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
import numpy as np


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_audio_path(temp_dir: Path) -> Path:
    """Create a sample audio file path (not actual audio, just path)."""
    audio_path = temp_dir / "sample.wav"
    audio_path.touch()
    return audio_path


@pytest.fixture
def sample_audio_data() -> np.ndarray:
    """Generate sample audio data (1 second of sine wave at 16kHz)."""
    sample_rate = 16000
    duration = 1.0
    frequency = 440.0  # A4 note
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t).astype(np.float32)
    return audio


@pytest.fixture
def sample_segments() -> list[dict]:
    """Sample transcription segments for testing."""
    return [
        {
            "start": 0.0,
            "end": 2.5,
            "text": "Hello, this is a test.",
            "speaker": "SPEAKER_00",
            "words": [
                {"word": "Hello", "start": 0.0, "end": 0.5},
                {"word": "this", "start": 0.6, "end": 0.8},
                {"word": "is", "start": 0.9, "end": 1.0},
                {"word": "a", "start": 1.1, "end": 1.2},
                {"word": "test", "start": 1.3, "end": 2.5},
            ],
        },
        {
            "start": 3.0,
            "end": 5.5,
            "text": "This is another speaker talking.",
            "speaker": "SPEAKER_01",
            "words": [
                {"word": "This", "start": 3.0, "end": 3.2},
                {"word": "is", "start": 3.3, "end": 3.4},
                {"word": "another", "start": 3.5, "end": 4.0},
                {"word": "speaker", "start": 4.1, "end": 4.5},
                {"word": "talking", "start": 4.6, "end": 5.5},
            ],
        },
    ]


@pytest.fixture
def mock_whisper_result() -> dict:
    """Mock result from faster-whisper transcription."""
    return {
        "segments": [
            {
                "start": 0.0,
                "end": 2.5,
                "text": "Hello, this is a test.",
                "words": [
                    {"word": "Hello", "start": 0.0, "end": 0.5, "probability": 0.95},
                    {"word": "this", "start": 0.6, "end": 0.8, "probability": 0.98},
                    {"word": "is", "start": 0.9, "end": 1.0, "probability": 0.99},
                    {"word": "a", "start": 1.1, "end": 1.2, "probability": 0.97},
                    {"word": "test", "start": 1.3, "end": 2.5, "probability": 0.96},
                ],
            }
        ],
        "language": "en",
    }


@pytest.fixture
def settings_ini(temp_dir: Path) -> Path:
    """Create a test settings.ini file."""
    settings_path = temp_dir / "settings.ini"
    settings_content = """[Paths]
input_dir = data/inputs
output_dir = data/outputs

[Models]
whisper_model = large-v3
diarization_model = pyannote/speaker-diarization

[Diarization]
mode = whisperx
vad_threshold = 0.5

[Export]
formats = txt,json,srt

[GPU]
device_ids = 0,1
"""
    settings_path.write_text(settings_content)
    return settings_path


@pytest.fixture
def mock_gpu_available(monkeypatch):
    """Mock GPU availability."""
    def mock_cuda_is_available():
        return True

    def mock_cuda_device_count():
        return 2

    monkeypatch.setattr("torch.cuda.is_available", mock_cuda_is_available)
    monkeypatch.setattr("torch.cuda.device_count", mock_cuda_device_count)


@pytest.fixture
def mock_no_gpu(monkeypatch):
    """Mock no GPU availability."""
    def mock_cuda_is_available():
        return False

    def mock_cuda_device_count():
        return 0

    monkeypatch.setattr("torch.cuda.is_available", mock_cuda_is_available)
    monkeypatch.setattr("torch.cuda.device_count", mock_cuda_device_count)
