"""
Faster Whisper transcription module.

Uses faster-whisper (CTranslate2) for efficient GPU-accelerated transcription.
"""

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional

from faster_whisper import WhisperModel

from pipeline.gpu_utils import get_memory_info, select_device, suggest_model_for_vram
from pipeline.logger import get_logger
from pipeline.preprocess import AudioPreprocessor


class FasterWhisperTranscriber:
    """Transcriber using faster-whisper for GPU-accelerated processing."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cuda",
        compute_type: str = "float16",
        logger=None,
        # Preprocessing options
        enable_preprocessing: bool = False,
        denoise: bool = False,
        denoise_method: str = "noisereduce",
        loudnorm: bool = False,
        trim_silence: bool = False,
        silence_threshold_db: float = -40.0,
        high_pass_filter: bool = False,
        hpf_cutoff: int = 80,
    ):
        """
        Initialize the transcriber.

        Args:
            model_size: Model size (base, small, medium.en, large-v3)
            device: Device to use (cuda, cpu, or auto)
            compute_type: Compute precision (float16, int8, etc.)
            logger: Optional logger instance
            enable_preprocessing: Enable audio preprocessing before transcription
            denoise: Enable denoising
            denoise_method: 'noisereduce' or 'ffmpeg'
            loudnorm: Enable loudness normalization
            trim_silence: Enable silence trimming
            silence_threshold_db: Silence threshold in dB (default: -40)
            high_pass_filter: Enable high-pass filter
            hpf_cutoff: High-pass filter cutoff frequency (Hz)
        """
        self.logger = logger or get_logger(__name__)

        # Preprocessing configuration
        self.enable_preprocessing = enable_preprocessing
        self.preprocessor = None
        if enable_preprocessing:
            self.preprocessor = AudioPreprocessor(
                denoise=denoise,
                denoise_method=denoise_method,
                loudnorm=loudnorm,
                trim_silence=trim_silence,
                silence_threshold_db=silence_threshold_db,
                high_pass_filter=high_pass_filter,
                hpf_cutoff=hpf_cutoff,
            )
            self.logger.info(
                "Audio preprocessing enabled",
                denoise=denoise,
                loudnorm=loudnorm,
                trim_silence=trim_silence,
                high_pass_filter=high_pass_filter,
            )

        # Auto-select device if needed
        selected_device = select_device(device, self.logger)

        # Check VRAM and suggest model if using GPU
        if selected_device == "cuda":
            mem_info = get_memory_info(0)
            if "error" not in mem_info:
                self.logger.info(
                    f"GPU memory: {mem_info['free_gb']} GB free / "
                    f"{mem_info['total_gb']} GB total"
                )

                suggested_model = suggest_model_for_vram(mem_info["free_gb"])
                if model_size == "large-v3" and mem_info["free_gb"] < 10:
                    self.logger.warning(
                        f"Model '{model_size}' may require more VRAM than "
                        f"available. Consider using '{suggested_model}' "
                        f"model for {mem_info['free_gb']} GB VRAM"
                    )

        # Adjust compute type for CPU
        if selected_device == "cpu":
            if compute_type == "float16":
                compute_type = "int8"
                self.logger.info("Adjusted compute_type to 'int8' for CPU (float16 not supported)")

        self.model_size = model_size
        self.device = selected_device
        self.compute_type = compute_type

        self.logger.info(
            "Initializing transcriber",
            model_size=model_size,
            device=selected_device,
            compute_type=compute_type,
        )
        self.model = WhisperModel(model_size, device=selected_device, compute_type=compute_type)

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        word_timestamps: bool = True,
    ) -> Dict:
        """
        Transcribe audio file.

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en'). None for auto-detection.
            word_timestamps: Include word-level timestamps

        Returns:
            Dictionary with transcription results
        """
        start_time = time.time()
        preprocessing_metrics = None
        temp_file = None

        # Apply preprocessing if enabled
        if self.enable_preprocessing and self.preprocessor:
            self.logger.info("Applying audio preprocessing before transcription")
            try:
                preprocessed_path, preprocessing_metrics = self.preprocessor.process(
                    Path(audio_path)
                )
                audio_path = str(preprocessed_path)
                temp_file = preprocessed_path
                self.logger.info(
                    "Preprocessing complete",
                    steps=len(preprocessing_metrics.get("steps_applied", [])),
                )
            except Exception as e:
                self.logger.warning(
                    f"Preprocessing failed, using original audio: {e}",
                    error=str(e),
                )

        segments, info = self.model.transcribe(
            audio_path,
            language=language,
            word_timestamps=word_timestamps,
            vad_filter=True,
        )

        # Convert segments generator to list and extract data
        segments_list = []
        full_text = []

        for segment in segments:
            segment_dict = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
            }

            if word_timestamps and segment.words:
                segment_dict["words"] = [
                    {
                        "start": word.start,
                        "end": word.end,
                        "word": word.word,
                        "probability": word.probability,
                    }
                    for word in segment.words
                ]

            segments_list.append(segment_dict)
            full_text.append(segment.text.strip())

        elapsed_time = time.time() - start_time

        # Calculate RTF (Real-Time Factor)
        # RTF = processing_time / audio_duration
        # Lower is better (RTF < 1.0 means faster than realtime)
        audio_duration = segments_list[-1]["end"] if segments_list else 0
        rtf = elapsed_time / audio_duration if audio_duration > 0 else 0

        result = {
            "text": " ".join(full_text),
            "segments": segments_list,
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": audio_duration,
            "processing_time": elapsed_time,
            "rtf": rtf,
            "model_size": self.model_size,
            "device": self.device,
        }

        # Add preprocessing metrics if available
        if preprocessing_metrics:
            result["preprocessing"] = preprocessing_metrics

        # Clean up temporary preprocessed file
        if temp_file and temp_file.exists():
            try:
                temp_file.unlink()
            except Exception as e:
                self.logger.warning(f"Failed to delete temp file {temp_file}: {e}")

        return result


def transcribe_file(
    audio_path: str,
    output_dir: Optional[str] = None,
    model_size: str = "base",
    device: str = "cuda",
    language: Optional[str] = None,
    # Preprocessing options
    enable_preprocessing: bool = False,
    denoise: bool = False,
    denoise_method: str = "noisereduce",
    loudnorm: bool = False,
    trim_silence: bool = False,
    silence_threshold_db: float = -40.0,
    high_pass_filter: bool = False,
    hpf_cutoff: int = 80,
) -> Dict:
    """
    Transcribe a single audio file and save outputs.

    Args:
        audio_path: Path to audio file
        output_dir: Directory for outputs (default: same as input)
        model_size: Model size to use
        device: Device to use (cuda or cpu)
        language: Language code or None for auto-detection
        enable_preprocessing: Enable audio preprocessing
        denoise: Enable denoising
        denoise_method: 'noisereduce' or 'ffmpeg'
        loudnorm: Enable loudness normalization
        trim_silence: Enable silence trimming
        silence_threshold_db: Silence threshold in dB
        high_pass_filter: Enable high-pass filter
        hpf_cutoff: High-pass filter cutoff frequency (Hz)

    Returns:
        Transcription results dictionary
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Set output directory
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = audio_path.parent

    # Initialize transcriber with preprocessing options
    transcriber = FasterWhisperTranscriber(
        model_size=model_size,
        device=device,
        enable_preprocessing=enable_preprocessing,
        denoise=denoise,
        denoise_method=denoise_method,
        loudnorm=loudnorm,
        trim_silence=trim_silence,
        silence_threshold_db=silence_threshold_db,
        high_pass_filter=high_pass_filter,
        hpf_cutoff=hpf_cutoff,
    )

    # Transcribe
    print(f"Transcribing {audio_path.name} with {model_size} model...")
    result = transcriber.transcribe(str(audio_path), language=language)

    # Print stats
    print(f"Duration: {result['duration']:.2f}s")
    print(f"Processing time: {result['processing_time']:.2f}s")
    print(f"RTF: {result['rtf']:.3f}")
    print(f"Language: {result['language']} " f"(confidence: {result['language_probability']:.2%})")

    # Save outputs
    base_name = audio_path.stem

    # Save text
    txt_path = output_dir / f"{base_name}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(result["text"])
    print(f"Saved text to {txt_path}")

    # Save JSON
    json_path = output_dir / f"{base_name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Saved JSON to {json_path}")

    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Transcribe audio using faster-whisper")
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument(
        "--model-size",
        default="base",
        choices=["tiny", "base", "small", "medium", "medium.en", "large-v3"],
        help="Whisper model size (default: base)",
    )
    parser.add_argument(
        "--device",
        default="cuda",
        choices=["cuda", "cpu", "auto"],
        help="Device to use: 'cuda', 'cpu', or 'auto' (default: cuda)",
    )
    parser.add_argument(
        "--language", help="Language code (e.g., 'en'). Auto-detect if not specified."
    )
    parser.add_argument("--output-dir", help="Output directory (default: same as input file)")

    # Preprocessing options
    preproc_group = parser.add_argument_group("Audio Preprocessing")
    preproc_group.add_argument(
        "--preprocess",
        action="store_true",
        help="Enable audio preprocessing before transcription",
    )
    preproc_group.add_argument("--denoise", action="store_true", help="Enable denoising")
    preproc_group.add_argument(
        "--denoise-method",
        choices=["noisereduce", "ffmpeg"],
        default="noisereduce",
        help="Denoising method (default: noisereduce)",
    )
    preproc_group.add_argument(
        "--loudnorm", action="store_true", help="Enable loudness normalization"
    )
    preproc_group.add_argument(
        "--trim-silence", action="store_true", help="Trim silence from audio"
    )
    preproc_group.add_argument(
        "--silence-threshold",
        type=float,
        default=-40.0,
        help="Silence threshold in dB (default: -40)",
    )
    preproc_group.add_argument(
        "--high-pass-filter", action="store_true", help="Enable high-pass filter"
    )
    preproc_group.add_argument(
        "--hpf-cutoff",
        type=int,
        default=80,
        help="High-pass filter cutoff (Hz, default: 80)",
    )

    args = parser.parse_args()

    try:
        transcribe_file(
            args.audio,
            output_dir=args.output_dir,
            model_size=args.model_size,
            device=args.device,
            language=args.language,
            # Preprocessing options
            enable_preprocessing=args.preprocess,
            denoise=args.denoise,
            denoise_method=args.denoise_method,
            loudnorm=args.loudnorm,
            trim_silence=args.trim_silence,
            silence_threshold_db=args.silence_threshold,
            high_pass_filter=args.high_pass_filter,
            hpf_cutoff=args.hpf_cutoff,
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
