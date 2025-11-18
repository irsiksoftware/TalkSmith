"""
WhisperX diarization pipeline.

Uses WhisperX for alignment and pyannote.audio for speaker diarization.
Requires HuggingFace token for pyannote models.
"""

import argparse
import json
import os
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import torch
import whisperx

from pipeline.logger import get_logger


class WhisperXDiarizer:
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
        self.logger = logger or get_logger(__name__)

        if not self.hf_token:
            raise ValueError(
                "HuggingFace token required for pyannote models. "
                "Set HF_TOKEN environment variable or pass hf_token parameter. "
                "Get token at: https://huggingface.co/settings/tokens"
            )

        self.logger.info(
            "Initializing WhisperX diarizer",
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            vad_onset=vad_onset,
            vad_offset=vad_offset,
        )

        # Suppress WhisperX warnings
        warnings.filterwarnings("ignore", category=UserWarning)

        # Load Whisper model
        self.logger.info("Loading Whisper model", model=model_size)
        self.model = whisperx.load_model(
            model_size,
            device=device,
            compute_type=compute_type,
        )

    def diarize(
        self,
        audio_path: str,
        language: Optional[str] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
    ) -> Dict:
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


def diarize_file(
    audio_path: str,
    output_dir: Optional[str] = None,
    model_size: str = "base",
    device: str = "cuda",
    language: Optional[str] = None,
    hf_token: Optional[str] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
    vad_onset: float = 0.5,
    vad_offset: float = 0.363,
) -> Dict:
    """
    Diarize a single audio file and save outputs.

    Args:
        audio_path: Path to audio file
        output_dir: Directory for outputs (default: same as input)
        model_size: Whisper model size
        device: Device to use (cuda or cpu)
        language: Language code or None for auto-detection
        hf_token: HuggingFace token for pyannote models
        min_speakers: Minimum number of speakers
        max_speakers: Maximum number of speakers
        vad_onset: VAD onset threshold
        vad_offset: VAD offset threshold

    Returns:
        Diarization results dictionary
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

    # Initialize diarizer with CPU fallback on OOM
    try:
        diarizer = WhisperXDiarizer(
            model_size=model_size,
            device=device,
            hf_token=hf_token,
            vad_onset=vad_onset,
            vad_offset=vad_offset,
        )
    except RuntimeError as e:
        if "out of memory" in str(e).lower() and device == "cuda":
            print(f"GPU OOM error: {e}")
            print("Falling back to CPU...")
            torch.cuda.empty_cache()
            device = "cpu"
            diarizer = WhisperXDiarizer(
                model_size=model_size,
                device=device,
                hf_token=hf_token,
                vad_onset=vad_onset,
                vad_offset=vad_offset,
            )
        else:
            raise

    # Diarize
    print(f"Diarizing {audio_path.name} with {model_size} model...")
    result = diarizer.diarize(
        str(audio_path),
        language=language,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
    )

    # Print stats
    print(f"Duration: {result['duration']:.2f}s")
    print(f"Processing time: {result['processing_time']:.2f}s")
    print(f"RTF: {result['rtf']:.3f}")
    print(f"Language: {result['language']}")
    print(f"Segments: {len(result['segments'])}")

    # Count speakers
    speakers = set()
    for segment in result["segments"]:
        if "speaker" in segment:
            speakers.add(segment["speaker"])
    if speakers:
        print(f"Speakers detected: {len(speakers)}")

    # Save outputs
    base_name = audio_path.stem

    # Save JSON with all data
    json_path = output_dir / f"{base_name}_diarized.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Saved JSON to {json_path}")

    # Save text with speaker labels
    txt_path = output_dir / f"{base_name}_diarized.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for segment in result["segments"]:
            speaker = segment.get("speaker", "UNKNOWN")
            text = segment["text"]
            f.write(f"[{speaker}] {text}\n")
    print(f"Saved text to {txt_path}")

    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Diarize audio using WhisperX + pyannote.audio")
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

    args = parser.parse_args()

    try:
        diarize_file(
            args.audio,
            output_dir=args.output_dir,
            model_size=args.model_size,
            device=args.device,
            language=args.language,
            hf_token=args.hf_token,
            min_speakers=args.min_speakers,
            max_speakers=args.max_speakers,
            vad_onset=args.vad_onset,
            vad_offset=args.vad_offset,
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
