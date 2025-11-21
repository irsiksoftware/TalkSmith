"""
Integration tests for audio preprocessing with transcription pipeline.

Tests the end-to-end integration between AudioPreprocessor and FasterWhisperTranscriber.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile as sf

from pipeline.preprocess import AudioPreprocessor
from pipeline.transcribe_fw import FasterWhisperTranscriber


@pytest.fixture
def sample_audio_file():
    """Create a temporary audio file for testing."""
    # Create a simple sine wave audio (440 Hz, 2 seconds)
    sample_rate = 16000
    duration = 2.0
    frequency = 440
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = 0.5 * np.sin(2 * np.pi * frequency * t)

    # Add some silence at beginning and end
    silence = np.zeros(int(sample_rate * 0.5))
    audio_with_silence = np.concatenate([silence, audio, silence])

    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio_with_silence, sample_rate)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def noisy_audio_file():
    """Create a temporary noisy audio file for testing."""
    # Create audio with background noise
    sample_rate = 16000
    duration = 2.0
    frequency = 440
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Signal + noise
    signal = 0.5 * np.sin(2 * np.pi * frequency * t)
    noise = 0.1 * np.random.randn(len(t))
    audio = signal + noise

    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio, sample_rate)
        temp_path = Path(f.name)

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


class TestPreprocessingIntegration:
    """Integration tests for preprocessing with transcription."""

    def test_preprocessor_creates_valid_audio(self, sample_audio_file):
        """Test that preprocessor creates valid audio file."""
        preprocessor = AudioPreprocessor(
            denoise=False, loudnorm=True, trim_silence=False, high_pass_filter=False
        )

        output_path, metrics = preprocessor.process(sample_audio_file)

        # Check output file exists and is valid
        assert output_path.exists()
        assert output_path.suffix == ".wav"

        # Load and verify audio
        audio, sr = sf.read(output_path)
        assert len(audio) > 0
        assert sr > 0

        # Check metrics
        assert "steps_applied" in metrics
        assert "loudness_normalization" in metrics["steps_applied"]
        assert metrics["sample_rate"] == 16000

        # Cleanup
        output_path.unlink()

    def test_preprocessing_with_all_steps(self, sample_audio_file):
        """Test preprocessing with all steps enabled."""
        preprocessor = AudioPreprocessor(
            denoise=True, loudnorm=True, trim_silence=True, high_pass_filter=True, hpf_cutoff=80
        )

        output_path, metrics = preprocessor.process(sample_audio_file)

        # Check all steps were applied
        assert len(metrics["steps_applied"]) >= 3  # At least 3 steps
        assert "loudness_normalization" in metrics["steps_applied"]
        assert "trim_silence" in metrics["steps_applied"]
        assert "high_pass_filter" in metrics["steps_applied"]

        # Verify trimming reduced duration
        if "silence_trimmed_seconds" in metrics:
            assert metrics["silence_trimmed_seconds"] > 0

        # Cleanup
        output_path.unlink()

    @patch("pipeline.transcribe_fw.WhisperModel")
    def test_transcriber_with_preprocessing_disabled(self, mock_whisper, sample_audio_file):
        """Test transcriber without preprocessing."""
        # Mock the transcribe method
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 2.0
        mock_segment.text = "Test transcription"
        mock_segment.words = []

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.95

        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        mock_whisper.return_value = mock_model

        # Initialize transcriber without preprocessing
        transcriber = FasterWhisperTranscriber(
            model_size="base",
            device="cpu",
            enable_preprocessing=False,
        )

        # Transcribe
        result = transcriber.transcribe(str(sample_audio_file))

        # Verify no preprocessing was applied
        assert "preprocessing" not in result
        assert result["text"] == "Test transcription"
        assert result["language"] == "en"

    @patch("pipeline.transcribe_fw.WhisperModel")
    def test_transcriber_with_preprocessing_enabled(self, mock_whisper, sample_audio_file):
        """Test transcriber with preprocessing enabled."""
        # Mock the transcribe method
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 2.0
        mock_segment.text = "Test transcription with preprocessing"
        mock_segment.words = []

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.95

        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        mock_whisper.return_value = mock_model

        # Initialize transcriber with preprocessing
        transcriber = FasterWhisperTranscriber(
            model_size="base",
            device="cpu",
            enable_preprocessing=True,
            denoise=False,  # Disable denoise to avoid noisereduce dependency issues
            loudnorm=True,
            trim_silence=True,
            high_pass_filter=False,  # Disable to avoid scipy dependency issues in CI
        )

        # Transcribe
        result = transcriber.transcribe(str(sample_audio_file))

        # Verify preprocessing was applied
        assert "preprocessing" in result
        assert "steps_applied" in result["preprocessing"]
        assert len(result["preprocessing"]["steps_applied"]) >= 1
        assert result["text"] == "Test transcription with preprocessing"

    @patch("pipeline.transcribe_fw.WhisperModel")
    def test_preprocessing_handles_errors_gracefully(self, mock_whisper, sample_audio_file):
        """Test that preprocessing errors are handled gracefully."""
        # Mock the transcribe method
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 2.0
        mock_segment.text = "Fallback transcription"
        mock_segment.words = []

        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.language_probability = 0.95

        mock_model.transcribe.return_value = ([mock_segment], mock_info)
        mock_whisper.return_value = mock_model

        # Create transcriber with preprocessing
        transcriber = FasterWhisperTranscriber(
            model_size="base",
            device="cpu",
            enable_preprocessing=True,
            loudnorm=True,
        )

        # Patch the preprocessor to raise an error
        with patch.object(transcriber.preprocessor, "process", side_effect=Exception("Test error")):
            # Should not raise, should fall back to original audio
            result = transcriber.transcribe(str(sample_audio_file))

        # Verify transcription still works with fallback
        assert result["text"] == "Fallback transcription"

    def test_preprocessing_metrics_in_result(self, sample_audio_file):
        """Test that preprocessing metrics are included in transcription result."""
        with patch("pipeline.transcribe_fw.WhisperModel") as mock_whisper:
            # Mock transcribe
            mock_model = MagicMock()
            mock_segment = MagicMock()
            mock_segment.start = 0.0
            mock_segment.end = 2.0
            mock_segment.text = "Test"
            mock_segment.words = []

            mock_info = MagicMock()
            mock_info.language = "en"
            mock_info.language_probability = 0.95

            mock_model.transcribe.return_value = ([mock_segment], mock_info)
            mock_whisper.return_value = mock_model

            # Initialize with preprocessing
            transcriber = FasterWhisperTranscriber(
                model_size="base",
                device="cpu",
                enable_preprocessing=True,
                loudnorm=True,
                trim_silence=True,
            )

            result = transcriber.transcribe(str(sample_audio_file))

            # Check preprocessing metrics structure
            assert "preprocessing" in result
            preprocessing = result["preprocessing"]
            assert "input_file" in preprocessing
            assert "output_file" in preprocessing
            assert "steps_applied" in preprocessing
            assert "original_duration_seconds" in preprocessing
            assert "final_duration_seconds" in preprocessing
            assert "sample_rate" in preprocessing

    def test_end_to_end_preprocessing_pipeline(self, noisy_audio_file):
        """Test complete end-to-end preprocessing pipeline."""
        # Test the preprocessor standalone
        preprocessor = AudioPreprocessor(
            denoise=True,
            denoise_method="noisereduce",
            loudnorm=True,
            trim_silence=False,  # Don't trim for this test
            high_pass_filter=True,
            hpf_cutoff=100,
        )

        try:
            output_path, metrics = preprocessor.process(noisy_audio_file)

            # Verify preprocessing completed
            assert output_path.exists()
            assert len(metrics["steps_applied"]) >= 2

            # Load both original and preprocessed
            original_audio, _ = sf.read(noisy_audio_file)
            processed_audio, _ = sf.read(output_path)

            # Audio should still have similar length (no trimming)
            assert abs(len(original_audio) - len(processed_audio)) < 1000

            # Peak levels should be normalized
            processed_peak = np.abs(processed_audio).max()
            target_peak = 10 ** (-3.0 / 20.0)  # -3 dBFS
            assert abs(processed_peak - target_peak) < 0.1

            # Cleanup
            output_path.unlink()

        except ImportError as e:
            # If dependencies are missing, skip the test
            pytest.skip(f"Preprocessing dependencies not available: {e}")
