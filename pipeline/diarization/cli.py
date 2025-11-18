"""Unified CLI for speaker diarization."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import torch

from pipeline.diarization import WhisperXDiarizer, AlternativeDiarizer


def diarize_file(
    audio_path: str,
    output_dir: Optional[str] = None,
    method: str = "alt",
    # WhisperX-specific params
    model_size: str = "base",
    device: str = "cuda",
    language: Optional[str] = None,
    hf_token: Optional[str] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
    vad_onset: float = 0.5,
    vad_offset: float = 0.363,
    # Alternative-specific params
    num_speakers: Optional[int] = None,
    window_size: float = 1.5,
    transcript_path: Optional[str] = None,
) -> dict:
    """
    Diarize a single audio file and save outputs.

    Args:
        audio_path: Path to audio file
        output_dir: Directory for outputs (default: same as input)
        method: Diarization method ('whisperx' or 'alt')
        model_size: Whisper model size (for WhisperX)
        device: Device to use (cuda or cpu)
        language: Language code (for WhisperX)
        hf_token: HuggingFace token (for WhisperX)
        min_speakers: Minimum number of speakers (for WhisperX)
        max_speakers: Maximum number of speakers (for WhisperX)
        vad_onset: VAD onset threshold (for WhisperX)
        vad_offset: VAD offset threshold (for WhisperX)
        num_speakers: Number of speakers (for Alternative)
        window_size: Window size in seconds (for Alternative)
        transcript_path: Path to transcript JSON (for Alternative)

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

    # Load transcript if provided
    transcript_segments = None
    if transcript_path:
        transcript_path = Path(transcript_path)
        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {transcript_path}")

        with open(transcript_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            transcript_segments = data.get("segments", data)

    # Initialize diarizer based on method
    if method == "whisperx":
        print(f"Diarizing {audio_path.name} with WhisperX ({model_size} model)...")

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

        result = diarizer.diarize(
            str(audio_path),
            language=language,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )

        # Count speakers
        speakers = set()
        for segment in result["segments"]:
            if "speaker" in segment:
                speakers.add(segment["speaker"])

        # Print stats
        print(f"Duration: {result['duration']:.2f}s")
        print(f"Processing time: {result['processing_time']:.2f}s")
        print(f"RTF: {result['rtf']:.3f}")
        print(f"Language: {result['language']}")
        print(f"Segments: {len(result['segments'])}")
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

    elif method == "alt":
        print(f"Diarizing {audio_path.name} with Alternative method...")

        diarizer = AlternativeDiarizer(window_size=window_size)
        segments = diarizer.diarize(
            str(audio_path),
            num_speakers=num_speakers,
            transcript_segments=transcript_segments,
        )

        # Determine output path
        output_path = output_dir / f"{audio_path.stem}_diarized.json"

        # Save results
        result = {
            "audio_file": str(audio_path),
            "num_speakers": len(set(seg["speaker"] for seg in segments)),
            "num_segments": len(segments),
            "segments": segments,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print("\nDiarization Results:")
        print(f"  Speakers detected: {result['num_speakers']}")
        print(f"  Segments created: {result['num_segments']}")
        print(f"  Saved to: {output_path}")

    else:
        raise ValueError(f"Unknown diarization method: {method}")

    return result


def main():
    """Unified diarization CLI."""
    parser = argparse.ArgumentParser(
        description="Speaker diarization for TalkSmith"
    )
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument(
        "-o", "--output-dir",
        help="Output directory (default: same as input file)"
    )

    # Diarization method
    method_group = parser.add_mutually_exclusive_group(required=True)
    method_group.add_argument(
        "--whisperx",
        action="store_true",
        help="Use WhisperX diarization (requires HF token)",
    )
    method_group.add_argument(
        "--alt",
        action="store_true",
        help="Use alternative diarization (token-free)",
    )

    # WhisperX-specific args
    parser.add_argument(
        "--model-size",
        default="base",
        choices=["tiny", "base", "small", "medium", "medium.en", "large-v3"],
        help="Whisper model size (default: base)",
    )
    parser.add_argument(
        "--language",
        help="Language code (e.g., 'en'). Auto-detect if not specified.",
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

    # Alternative-specific args
    parser.add_argument(
        "--num-speakers",
        type=int,
        help="Number of speakers (for alternative method)",
    )
    parser.add_argument(
        "--window-size",
        type=float,
        default=1.5,
        help="Window size in seconds (default: 1.5, for alternative method)",
    )
    parser.add_argument(
        "--transcript",
        help="Path to transcript JSON for alignment (for alternative method)",
    )

    # Common args
    parser.add_argument(
        "--device",
        default="cuda",
        choices=["cuda", "cpu"],
        help="Device to use (default: cuda)",
    )

    args = parser.parse_args()

    try:
        # Determine method
        method = "whisperx" if args.whisperx else "alt"

        # Validate WhisperX requirements
        if method == "whisperx" and not args.hf_token:
            import os
            if not os.getenv("HF_TOKEN"):
                print("Error: WhisperX requires --hf-token or HF_TOKEN env var", file=sys.stderr)
                return 1

        diarize_file(
            audio_path=args.audio,
            output_dir=args.output_dir,
            method=method,
            model_size=args.model_size,
            device=args.device,
            language=args.language,
            hf_token=args.hf_token,
            min_speakers=args.min_speakers,
            max_speakers=args.max_speakers,
            vad_onset=args.vad_onset,
            vad_offset=args.vad_offset,
            num_speakers=args.num_speakers,
            window_size=args.window_size,
            transcript_path=args.transcript,
        )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
