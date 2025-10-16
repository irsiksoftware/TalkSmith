"""Unit tests for transcription module."""
import pytest


@pytest.mark.unit
class TestTranscription:
    """Tests for core transcription functionality."""

    def test_transcribe_basic(self, sample_audio_path):
        """Test basic transcription works."""
        # TODO: Implement when pipeline/transcribe_fw.py exists
        pass

    def test_transcribe_with_timestamps(self, sample_audio_path):
        """Test transcription includes word timestamps."""
        pass

    def test_model_loading(self):
        """Test Whisper model loads correctly."""
        pass

    def test_language_detection(self, sample_audio_path):
        """Test automatic language detection."""
        pass

    def test_invalid_audio_file(self, temp_dir):
        """Test error handling for invalid audio."""
        # invalid_path = temp_dir / "nonexistent.wav"
        # Should raise appropriate error when implemented
        pass
