"""
Unit tests for audio preprocessing module.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile as sf

from pipeline.preprocess import (
    AudioPreprocessor,
    preprocess_audio,
    NOISEREDUCE_AVAILABLE,
)


@pytest.mark.unit
class TestAudioPreprocessor:
    """Tests for AudioPreprocessor class."""

    def test_init_default(self):
        """Test AudioPreprocessor initialization with defaults."""
        preprocessor = AudioPreprocessor()
        assert preprocessor.denoise is False
        assert preprocessor.loudnorm is False
        assert preprocessor.trim_silence is False
        assert preprocessor.high_pass_filter is False

    def test_init_with_options(self):
        """Test AudioPreprocessor initialization with options."""
        preprocessor = AudioPreprocessor(
            denoise=True,
            denoise_method="ffmpeg",
            loudnorm=True,
            trim_silence=True,
            silence_threshold_db=-35.0,
            high_pass_filter=True,
            hpf_cutoff=100,
        )
        assert preprocessor.denoise is True
        assert preprocessor.denoise_method == "ffmpeg"
        assert preprocessor.loudnorm is True
        assert preprocessor.trim_silence is True
        assert preprocessor.silence_threshold_db == -35.0
        assert preprocessor.high_pass_filter is True
        assert preprocessor.hpf_cutoff == 100

    def test_process_no_operations(self, sample_audio_path):
        """Test processing with no operations enabled."""
        preprocessor = AudioPreprocessor()

        output_path, metrics = preprocessor.process(sample_audio_path)

        assert output_path.exists()
        assert metrics["steps_applied"] == []
        assert "original_duration_seconds" in metrics
        assert "final_duration_seconds" in metrics

    def test_process_with_output_path(self, sample_audio_path, temp_dir):
        """Test processing with specified output path."""
        output_path = temp_dir / "output.wav"
        preprocessor = AudioPreprocessor()

        result_path, metrics = preprocessor.process(sample_audio_path, output_path)

        assert result_path == output_path
        assert output_path.exists()

    def test_loudness_normalization(self, sample_audio_path):
        """Test loudness normalization."""
        preprocessor = AudioPreprocessor(loudnorm=True)

        output_path, metrics = preprocessor.process(sample_audio_path)

        assert "loudness_normalization" in metrics["steps_applied"]
        assert output_path.exists()

        # Verify audio was normalized
        audio, sr = sf.read(output_path)
        peak = np.abs(audio).max()
        target_peak = 10 ** (-3.0 / 20.0)  # -3 dBFS
        assert np.isclose(peak, target_peak, rtol=0.01)

    def test_trim_silence(self):
        """Test silence trimming."""
        # Create audio with silence at start and end
        sample_rate = 16000
        duration = 3.0
        num_samples = int(duration * sample_rate)

        # Create audio: 0.5s silence, 2s audio, 0.5s silence
        audio = np.zeros(num_samples)
        start_idx = int(0.5 * sample_rate)
        end_idx = int(2.5 * sample_rate)
        audio[start_idx:end_idx] = np.random.randn(end_idx - start_idx) * 0.1

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = Path(f.name)
            sf.write(temp_path, audio, sample_rate)

        try:
            preprocessor = AudioPreprocessor(
                trim_silence=True, silence_threshold_db=-40.0
            )
            output_path, metrics = preprocessor.process(temp_path)

            assert "trim_silence" in metrics["steps_applied"]
            assert "silence_trimmed_seconds" in metrics
            assert metrics["silence_trimmed_seconds"] > 0

            # Verify trimmed audio is shorter
            trimmed_audio, _ = sf.read(output_path)
            assert len(trimmed_audio) < len(audio)
        finally:
            temp_path.unlink()

    def test_high_pass_filter(self, sample_audio_path):
        """Test high-pass filter."""
        try:
            import scipy  # noqa: F401

            preprocessor = AudioPreprocessor(high_pass_filter=True, hpf_cutoff=80)
            output_path, metrics = preprocessor.process(sample_audio_path)

            assert "high_pass_filter" in metrics["steps_applied"]
            assert output_path.exists()
        except ImportError:
            pytest.skip("scipy not available")

    @pytest.mark.skipif(not NOISEREDUCE_AVAILABLE, reason="noisereduce not available")
    def test_denoise_noisereduce(self, sample_audio_path):
        """Test denoising with noisereduce."""
        preprocessor = AudioPreprocessor(denoise=True, denoise_method="noisereduce")
        output_path, metrics = preprocessor.process(sample_audio_path)

        assert "denoise_noisereduce" in metrics["steps_applied"]
        assert output_path.exists()

    def test_denoise_ffmpeg_fallback(self, sample_audio_path):
        """Test denoising with ffmpeg fallback."""
        preprocessor = AudioPreprocessor(denoise=True, denoise_method="ffmpeg")
        output_path, metrics = preprocessor.process(sample_audio_path)

        assert "denoise_ffmpeg" in metrics["steps_applied"]
        assert output_path.exists()

    def test_multiple_operations(self, sample_audio_path):
        """Test applying multiple preprocessing operations."""
        preprocessor = AudioPreprocessor(
            loudnorm=True, trim_silence=True, high_pass_filter=True
        )

        output_path, metrics = preprocessor.process(sample_audio_path)

        assert len(metrics["steps_applied"]) >= 2
        assert "loudness_normalization" in metrics["steps_applied"]
        assert output_path.exists()

    def test_empty_audio_handling(self):
        """Test handling of empty/silent audio."""
        # Create silent audio
        sample_rate = 16000
        duration = 1.0
        audio = np.zeros(int(duration * sample_rate))

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = Path(f.name)
            sf.write(temp_path, audio, sample_rate)

        try:
            preprocessor = AudioPreprocessor(trim_silence=True)
            output_path, metrics = preprocessor.process(temp_path)

            # Should handle gracefully
            assert output_path.exists()
        finally:
            temp_path.unlink()


@pytest.mark.unit
class TestPreprocessAudioFunction:
    """Tests for preprocess_audio convenience function."""

    def test_preprocess_audio_basic(self, sample_audio_path):
        """Test basic preprocessing."""
        output_path, metrics = preprocess_audio(sample_audio_path, loudnorm=True)

        assert output_path.exists()
        assert "loudness_normalization" in metrics["steps_applied"]

    def test_preprocess_audio_with_output(self, sample_audio_path, temp_dir):
        """Test preprocessing with output path."""
        output_path_specified = temp_dir / "output.wav"

        result_path, metrics = preprocess_audio(
            sample_audio_path, output_path=output_path_specified, loudnorm=True
        )

        assert result_path == output_path_specified
        assert output_path_specified.exists()

    def test_preprocess_audio_all_options(self, sample_audio_path):
        """Test preprocessing with all options enabled."""
        output_path, metrics = preprocess_audio(
            sample_audio_path,
            denoise=True,
            loudnorm=True,
            trim_silence=True,
            high_pass_filter=True,
        )

        assert output_path.exists()
        assert len(metrics["steps_applied"]) > 0


@pytest.mark.unit
class TestLoudnessNormalization:
    """Tests for loudness normalization."""

    def test_normalize_quiet_audio(self):
        """Test normalizing quiet audio."""
        sample_rate = 16000
        duration = 1.0

        # Create quiet audio
        audio = np.random.randn(int(duration * sample_rate)) * 0.01

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = Path(f.name)
            sf.write(temp_path, audio, sample_rate)

        try:
            preprocessor = AudioPreprocessor(loudnorm=True)
            output_path, _ = preprocessor.process(temp_path)

            # Verify audio was amplified
            normalized_audio, _ = sf.read(output_path)
            assert np.abs(normalized_audio).max() > np.abs(audio).max()
        finally:
            temp_path.unlink()

    def test_normalize_loud_audio(self):
        """Test normalizing loud audio."""
        sample_rate = 16000
        duration = 1.0

        # Create loud audio
        audio = np.random.randn(int(duration * sample_rate)) * 0.9

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = Path(f.name)
            sf.write(temp_path, audio, sample_rate)

        try:
            preprocessor = AudioPreprocessor(loudnorm=True)
            output_path, _ = preprocessor.process(temp_path)

            # Verify audio was attenuated
            normalized_audio, _ = sf.read(output_path)
            assert np.abs(normalized_audio).max() < np.abs(audio).max()
        finally:
            temp_path.unlink()


@pytest.mark.unit
class TestMetrics:
    """Tests for preprocessing metrics."""

    def test_metrics_duration_tracking(self, sample_audio_path):
        """Test that duration is tracked correctly."""
        preprocessor = AudioPreprocessor(loudnorm=True)
        _, metrics = preprocessor.process(sample_audio_path)

        assert "original_duration_seconds" in metrics
        assert "final_duration_seconds" in metrics
        assert "duration_change_seconds" in metrics
        assert metrics["original_duration_seconds"] > 0

    def test_metrics_steps_tracking(self, sample_audio_path):
        """Test that applied steps are tracked."""
        preprocessor = AudioPreprocessor(loudnorm=True, trim_silence=True)
        _, metrics = preprocessor.process(sample_audio_path)

        assert "steps_applied" in metrics
        assert isinstance(metrics["steps_applied"], list)
        assert len(metrics["steps_applied"]) >= 1

    def test_metrics_sample_rate(self, sample_audio_path):
        """Test that sample rate is recorded."""
        preprocessor = AudioPreprocessor()
        _, metrics = preprocessor.process(sample_audio_path)

        assert "sample_rate" in metrics
        assert metrics["sample_rate"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
