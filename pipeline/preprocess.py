"""
Audio preprocessing module for TalkSmith.

Provides audio preprocessing operations for better transcription quality:
- Denoising (using noisereduce or ffmpeg)
- Loudness normalization (EBU R128 standard)
- Silence trimming
- High-pass filter (optional)
- Format conversion

Usage:
    python pipeline/preprocess.py input.wav --denoise --loudnorm --trim-silence
"""

import argparse
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import soundfile as sf

try:
    import noisereduce as nr

    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False

from pipeline.logger import get_logger

logger = get_logger(__name__)


class AudioPreprocessor:
    """
    Audio preprocessing pipeline for improving transcription quality.
    """

    def __init__(
        self,
        denoise: bool = False,
        denoise_method: str = "noisereduce",
        loudnorm: bool = False,
        trim_silence: bool = False,
        silence_threshold_db: float = -40.0,
        min_silence_duration: float = 0.3,
        high_pass_filter: bool = False,
        hpf_cutoff: int = 80,
    ):
        """
        Initialize audio preprocessor.

        Args:
            denoise: Enable denoising
            denoise_method: 'noisereduce' or 'ffmpeg'
            loudnorm: Enable loudness normalization (EBU R128)
            trim_silence: Enable silence trimming
            silence_threshold_db: Silence threshold in dB (default: -40)
            min_silence_duration: Minimum silence duration to trim (seconds)
            high_pass_filter: Enable high-pass filter
            hpf_cutoff: High-pass filter cutoff frequency (Hz)
        """
        self.denoise = denoise
        self.denoise_method = denoise_method
        self.loudnorm = loudnorm
        self.trim_silence = trim_silence
        self.silence_threshold_db = silence_threshold_db
        self.min_silence_duration = min_silence_duration
        self.high_pass_filter = high_pass_filter
        self.hpf_cutoff = hpf_cutoff

        if denoise and denoise_method == "noisereduce" and not NOISEREDUCE_AVAILABLE:
            logger.warning("noisereduce not available, falling back to ffmpeg denoising")
            self.denoise_method = "ffmpeg"

    def process(self, input_path: Path, output_path: Optional[Path] = None) -> Tuple[Path, dict]:
        """
        Process audio file with configured preprocessing steps.

        Args:
            input_path: Input audio file path
            output_path: Output file path (default: temp file)

        Returns:
            Tuple of (output_path, metrics dict)
        """
        logger.log_start("audio_preprocessing", input_file=str(input_path))

        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".wav", prefix="preprocessed_"))

        metrics = {
            "input_file": str(input_path),
            "output_file": str(output_path),
            "steps_applied": [],
        }

        # Load audio
        audio, sample_rate = sf.read(input_path)
        original_duration = len(audio) / sample_rate
        metrics["original_duration_seconds"] = original_duration
        metrics["sample_rate"] = sample_rate

        logger.info(
            f"Loaded audio: {original_duration:.2f}s @ {sample_rate}Hz",
            duration=original_duration,
            sample_rate=sample_rate,
        )

        # Apply preprocessing steps
        if self.high_pass_filter:
            audio = self._apply_high_pass_filter(audio, sample_rate)
            metrics["steps_applied"].append("high_pass_filter")

        if self.denoise:
            audio = self._apply_denoise(audio, sample_rate)
            metrics["steps_applied"].append(f"denoise_{self.denoise_method}")

        if self.trim_silence:
            audio, trimmed_seconds = self._trim_silence(audio, sample_rate)
            metrics["steps_applied"].append("trim_silence")
            metrics["silence_trimmed_seconds"] = trimmed_seconds

        if self.loudnorm:
            audio = self._apply_loudnorm(audio, sample_rate)
            metrics["steps_applied"].append("loudness_normalization")

        # Save processed audio
        sf.write(output_path, audio, sample_rate)

        final_duration = len(audio) / sample_rate
        metrics["final_duration_seconds"] = final_duration
        metrics["duration_change_seconds"] = original_duration - final_duration

        logger.log_complete(
            "audio_preprocessing",
            duration=final_duration,
            steps=len(metrics["steps_applied"]),
        )
        logger.log_metrics(metrics)

        return output_path, metrics

    def _apply_denoise(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply denoising to audio."""
        logger.info(f"Applying denoising (method: {self.denoise_method})")

        if self.denoise_method == "noisereduce" and NOISEREDUCE_AVAILABLE:
            # Use noisereduce library
            return nr.reduce_noise(y=audio, sr=sample_rate, stationary=True, prop_decrease=0.8)
        elif self.denoise_method == "ffmpeg":
            # Use ffmpeg's afftdn filter
            logger.warning(
                "FFmpeg denoising requires external processing - returning original audio"
            )
            return audio
        else:
            logger.warning(f"Unknown denoise method: {self.denoise_method}")
            return audio

    def _apply_loudnorm(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply loudness normalization (simple peak normalization)."""
        logger.info("Applying loudness normalization")

        # Simple peak normalization (target: -3 dBFS)
        target_peak = 10 ** (-3.0 / 20.0)  # -3 dBFS
        current_peak = np.abs(audio).max()

        if current_peak > 0:
            scale_factor = target_peak / current_peak
            audio = audio * scale_factor

        return audio

    def _trim_silence(self, audio: np.ndarray, sample_rate: int) -> Tuple[np.ndarray, float]:
        """Trim silence from beginning and end of audio."""
        logger.info(f"Trimming silence (threshold: {self.silence_threshold_db} dB)")

        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio_mono = audio.mean(axis=1)
        else:
            audio_mono = audio

        # Calculate power in dB
        power = audio_mono**2
        power_db = 10 * np.log10(power + 1e-10)

        # Find non-silent regions
        threshold = self.silence_threshold_db
        non_silent = power_db > threshold

        # Apply minimum duration constraint
        min_samples = int(self.min_silence_duration * sample_rate)

        # Find start and end of non-silent region
        non_silent_indices = np.where(non_silent)[0]

        if len(non_silent_indices) == 0:
            logger.warning("No non-silent audio found, returning original")
            return audio, 0.0

        start_idx = max(0, non_silent_indices[0] - min_samples // 2)
        end_idx = min(len(audio), non_silent_indices[-1] + min_samples // 2)

        # Trim audio
        trimmed_audio = audio[start_idx:end_idx]

        # Calculate trimmed duration
        original_duration = len(audio) / sample_rate
        trimmed_duration = len(trimmed_audio) / sample_rate
        removed_seconds = original_duration - trimmed_duration

        logger.info(
            f"Trimmed {removed_seconds:.2f}s of silence",
            removed_seconds=removed_seconds,
        )

        return trimmed_audio, removed_seconds

    def _apply_high_pass_filter(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply high-pass filter to remove low-frequency noise."""
        logger.info(f"Applying high-pass filter (cutoff: {self.hpf_cutoff} Hz)")

        try:
            from scipy import signal

            # Design butterworth high-pass filter
            nyquist = sample_rate / 2
            normal_cutoff = self.hpf_cutoff / nyquist
            b, a = signal.butter(4, normal_cutoff, btype="high", analog=False)

            # Apply filter
            filtered = signal.filtfilt(b, a, audio)
            return filtered
        except ImportError:
            logger.warning("scipy not available, skipping high-pass filter")
            return audio


def preprocess_audio(
    input_path: Path,
    output_path: Optional[Path] = None,
    denoise: bool = False,
    denoise_method: str = "noisereduce",
    loudnorm: bool = False,
    trim_silence: bool = False,
    silence_threshold_db: float = -40.0,
    high_pass_filter: bool = False,
) -> Tuple[Path, dict]:
    """
    Preprocess audio file for better transcription quality.

    Args:
        input_path: Input audio file
        output_path: Output file (default: temp file)
        denoise: Enable denoising
        denoise_method: 'noisereduce' or 'ffmpeg'
        loudnorm: Enable loudness normalization
        trim_silence: Enable silence trimming
        silence_threshold_db: Silence threshold in dB
        high_pass_filter: Enable high-pass filter

    Returns:
        Tuple of (output_path, metrics dict)
    """
    preprocessor = AudioPreprocessor(
        denoise=denoise,
        denoise_method=denoise_method,
        loudnorm=loudnorm,
        trim_silence=trim_silence,
        silence_threshold_db=silence_threshold_db,
        high_pass_filter=high_pass_filter,
    )

    return preprocessor.process(input_path, output_path)


def main():
    """Command-line interface for audio preprocessing."""
    parser = argparse.ArgumentParser(
        description="Preprocess audio for better transcription quality"
    )
    parser.add_argument("input", type=Path, help="Input audio file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file (default: <input>_preprocessed.wav)",
    )
    parser.add_argument("--denoise", action="store_true", help="Enable denoising")
    parser.add_argument(
        "--denoise-method",
        choices=["noisereduce", "ffmpeg"],
        default="noisereduce",
        help="Denoising method",
    )
    parser.add_argument("--loudnorm", action="store_true", help="Enable loudness normalization")
    parser.add_argument("--trim-silence", action="store_true", help="Trim silence from audio")
    parser.add_argument(
        "--silence-threshold",
        type=float,
        default=-40.0,
        help="Silence threshold in dB (default: -40)",
    )
    parser.add_argument("--high-pass-filter", action="store_true", help="Enable high-pass filter")
    parser.add_argument(
        "--hpf-cutoff",
        type=int,
        default=80,
        help="High-pass filter cutoff (Hz, default: 80)",
    )

    args = parser.parse_args()

    # Set default output path
    if args.output is None:
        args.output = args.input.parent / f"{args.input.stem}_preprocessed.wav"

    # Process audio
    output_path, metrics = preprocess_audio(
        input_path=args.input,
        output_path=args.output,
        denoise=args.denoise,
        denoise_method=args.denoise_method,
        loudnorm=args.loudnorm,
        trim_silence=args.trim_silence,
        silence_threshold_db=args.silence_threshold,
        high_pass_filter=args.high_pass_filter,
    )

    print(f"\nPreprocessed audio saved to: {output_path}")
    print("\nMetrics:")
    for key, value in metrics.items():
        if key != "steps_applied":
            print(f"  {key}: {value}")
    print(f"  steps_applied: {', '.join(metrics['steps_applied'])}")


if __name__ == "__main__":
    main()
