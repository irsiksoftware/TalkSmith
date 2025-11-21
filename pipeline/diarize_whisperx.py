"""
WhisperX diarization pipeline.

Uses WhisperX for alignment and pyannote.audio for speaker diarization.
Requires HuggingFace token for pyannote models.
"""

import argparse
import os
import time
import warnings
from typing import Any, Dict, List, Optional

import torch
import whisperx

from pipeline.diarization_base import DiarizationBase


class WhisperXDiarizer(DiarizationBase):
    """Diarizer using WhisperX + pyannote.audio for speaker diarization."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cuda",
        compute_type: str = "float16",
        hf_token: Optional[str] = None,
        vad_onset: float = 0.5,
        vad_offset: float = 0.363,
        logger=None,
    ):
        """
        Initialize the diarizer.

        Args:
            model_size: Whisper model size (base, small, medium.en, large-v3)
            device: Device to use (cuda or cpu)
            compute_type: Compute precision (float16, int8)
            hf_token: HuggingFace token for pyannote models
            vad_onset: VAD onset threshold (0.0-1.0)
            vad_offset: VAD offset threshold (0.0-1.0)
            logger: Optional logger instance
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        self.vad_onset = vad_onset
        self.vad_offset = vad_offset

        if not self.hf_token:
            raise ValueError(
                "HuggingFace token required for pyannote models. "
                "Set HF_TOKEN environment variable or pass hf_token parameter. "
                "Get token at: https://huggingface.co/settings/tokens"
            )

        # Suppress WhisperX warnings
        warnings.filterwarnings("ignore", category=UserWarning)

        # Initialize base class (which calls _initialize_models)
        super().__init__(logger=logger)

    def _initialize_models(self):
        """Initialize WhisperX models."""
        self.logger.info(
            "Initializing WhisperX diarizer",
            model_size=self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            vad_onset=self.vad_onset,
            vad_offset=self.vad_offset,
        )

        # Load Whisper model
        self.logger.info("Loading Whisper model", model=self.model_size)
        self.model = whisperx.load_model(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )

    def _perform_diarization(
        self,
        audio_path: str,
        language: Optional[str] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Transcribe and diarize audio file.

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en'). None for auto-detection.
            min_speakers: Minimum number of speakers (None for auto-detection)
            max_speakers: Maximum number of speakers (None for auto-detection)

        Returns:
            Dictionary with diarized segments: {start, end, speaker, text}
        """
        start_time = time.time()
        audio_path = str(audio_path)

        self.logger.info(
            "Starting diarization",
            audio_path=audio_path,
            language=language,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )

        # Step 1: Load audio
        self.logger.info("Loading audio", audio_path=audio_path)
        audio = whisperx.load_audio(audio_path)

        # Step 2: Transcribe with Whisper
        self.logger.info("Transcribing audio", model=self.model_size)
        transcribe_start = time.time()
        result = self.model.transcribe(
            audio,
            language=language,
            batch_size=16,
        )
        transcribe_time = time.time() - transcribe_start
        self.logger.info(
            "Transcription complete",
            duration=transcribe_time,
            segments=len(result.get("segments", [])),
            language=result.get("language"),
        )

        detected_language = result.get("language", language or "en")

        # Step 3: Align whisper output
        self.logger.info("Aligning segments", language=detected_language)
        align_start = time.time()

        try:
            model_a, metadata = whisperx.load_align_model(
                language_code=detected_language,
                device=self.device,
            )
            result = whisperx.align(
                result["segments"],
                model_a,
                metadata,
                audio,
                self.device,
                return_char_alignments=False,
            )
            align_time = time.time() - align_start
            self.logger.info("Alignment complete", duration=align_time)
        except Exception as e:
            self.logger.warning(
                "Alignment failed, using original timestamps",
                error=str(e),
            )
            align_time = 0

        # Step 4: Diarize with pyannote
        self.logger.info("Loading diarization model")
        diarize_start = time.time()

        try:
            diarize_model = whisperx.DiarizationPipeline(
                use_auth_token=self.hf_token,
                device=self.device,
            )

            # Apply diarization
            diarize_segments = diarize_model(
                audio,
                min_speakers=min_speakers,
                max_speakers=max_speakers,
            )

            # Assign speaker labels to words
            result = whisperx.assign_word_speakers(diarize_segments, result)
            diarize_time = time.time() - diarize_start
            self.logger.info("Diarization complete", duration=diarize_time)
        except Exception as e:
            self.logger.error(
                "Diarization failed",
                error=str(e),
            )
            # Continue without speaker labels
            diarize_time = 0

        # Step 5: Format output
        segments = self._format_segments(result.get("segments", []))

        total_time = time.time() - start_time
        audio_duration = segments[-1]["end"] if segments else 0
        rtf = total_time / audio_duration if audio_duration > 0 else 0

        output = {
            "segments": segments,
            "language": detected_language,
            "duration": audio_duration,
            "processing_time": total_time,
            "rtf": rtf,
            "model_size": self.model_size,
            "device": self.device,
            "timings": {
                "transcribe": transcribe_time,
                "align": align_time,
                "diarize": diarize_time,
            },
        }

        self.logger.info(
            "Diarization complete",
            duration=audio_duration,
            processing_time=total_time,
            rtf=rtf,
            segments=len(segments),
        )

        return output

    def _format_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Format WhisperX segments to standard format.

        Args:
            segments: Raw WhisperX segments

        Returns:
            List of formatted segments: {start, end, text, speaker}
        """
        formatted = []

        for segment in segments:
            formatted_segment = {
                "start": segment.get("start", 0.0),
                "end": segment.get("end", 0.0),
                "text": segment.get("text", "").strip(),
            }

            # Add speaker if available
            if "speaker" in segment:
                formatted_segment["speaker"] = segment["speaker"]

            # Add words if available
            if "words" in segment and segment["words"]:
                formatted_segment["words"] = [
                    {
                        "start": word.get("start", 0.0),
                        "end": word.get("end", 0.0),
                        "word": word.get("word", ""),
                        "speaker": word.get("speaker"),
                    }
                    for word in segment["words"]
                ]

            formatted.append(formatted_segment)

        return formatted

    @classmethod
    def _get_cli_parser(cls) -> argparse.ArgumentParser:
        """Get CLI argument parser for WhisperX diarizer."""
        parser = argparse.ArgumentParser(
            description="Diarize audio using WhisperX + pyannote.audio"
        )
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
            choices=["cuda", "cpu"],
            help="Device to use (default: cuda)",
        )
        parser.add_argument(
            "--language",
            help="Language code (e.g., 'en'). Auto-detect if not specified.",
        )
        parser.add_argument(
            "--output-dir",
            help="Output directory (default: same as input file)",
        )
        parser.add_argument(
            "--hf-token",
            help="HuggingFace token (or set HF_TOKEN env var)",
        )
        parser.add_argument(
            "--min-speakers",
            type=int,
            help="Minimum number of speakers",
        )
        parser.add_argument(
            "--max-speakers",
            type=int,
            help="Maximum number of speakers",
        )
        parser.add_argument(
            "--vad-onset",
            type=float,
            default=0.5,
            help="VAD onset threshold (0.0-1.0, default: 0.5)",
        )
        parser.add_argument(
            "--vad-offset",
            type=float,
            default=0.363,
            help="VAD offset threshold (0.0-1.0, default: 0.363)",
        )
        return parser

    @classmethod
    def _extract_diarizer_kwargs(cls, args: argparse.Namespace) -> Dict[str, Any]:
        """Extract constructor kwargs from parsed arguments."""
        return {
            "model_size": args.model_size,
            "device": args.device,
            "hf_token": args.hf_token,
            "vad_onset": args.vad_onset,
            "vad_offset": args.vad_offset,
        }

    @classmethod
    def _extract_diarization_kwargs(cls, args: argparse.Namespace) -> Dict[str, Any]:
        """Extract diarization kwargs from parsed arguments."""
        return {
            "language": args.language,
            "min_speakers": args.min_speakers,
            "max_speakers": args.max_speakers,
        }

    @classmethod
    def diarize_file_with_oom_fallback(
        cls,
        audio_path: str,
        output_dir: Optional[str] = None,
        model_size: str = "base",
        device: str = "cuda",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Diarize a file with automatic CPU fallback on GPU OOM errors.

        Args:
            audio_path: Path to audio file
            output_dir: Output directory
            model_size: Whisper model size
            device: Device to use (cuda or cpu)
            **kwargs: Additional diarization parameters

        Returns:
            Diarization results
        """
        try:
            diarizer = cls(model_size=model_size, device=device, **kwargs)
        except RuntimeError as e:
            if "out of memory" in str(e).lower() and device == "cuda":
                print(f"GPU OOM error: {e}")
                print("Falling back to CPU...")
                torch.cuda.empty_cache()
                device = "cpu"
                diarizer = cls(model_size=model_size, device=device, **kwargs)
            else:
                raise

        return diarizer.diarize_file(audio_path, output_dir=output_dir)


def main():
    """CLI entry point."""
    return WhisperXDiarizer.run_cli()


if __name__ == "__main__":
    exit(main())
