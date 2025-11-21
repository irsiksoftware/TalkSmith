"""Post-process speaker labels: normalize names and merge short utterances."""

import argparse
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from pipeline.logger import TalkSmithLogger


def normalize_speaker_names(
    segments: List[Dict[str, Any]],
    prefix: str = "Speaker",
    logger: Optional["TalkSmithLogger"] = None,
) -> List[Dict[str, Any]]:
    """
    Normalize speaker labels to human-readable format (e.g., Speaker 1, Speaker 2).

    Args:
        segments: List of segment dictionaries with 'speaker' field
        prefix: Prefix for normalized speaker names (default: "Speaker")
        logger: Optional logger instance

    Returns:
        List of segments with normalized speaker names
    """
    if not segments:
        return segments

    # Build mapping from original speaker IDs to normalized names
    unique_speakers = []
    for segment in segments:
        if "speaker" in segment:
            speaker = segment["speaker"]
            if speaker not in unique_speakers:
                unique_speakers.append(speaker)

    # Sort speakers to ensure consistent ordering
    unique_speakers.sort()
    speaker_mapping = {original: f"{prefix} {i + 1}" for i, original in enumerate(unique_speakers)}

    if logger:
        logger.debug(
            f"Normalizing {len(speaker_mapping)} speaker labels",
            speaker_count=len(speaker_mapping),
            mapping=speaker_mapping,
        )

    # Apply normalization
    normalized_segments = []
    for segment in segments:
        normalized_segment = segment.copy()
        if "speaker" in segment:
            normalized_segment["speaker"] = speaker_mapping[segment["speaker"]]
        normalized_segments.append(normalized_segment)

    if logger:
        logger.info("Speaker normalization complete", segment_count=len(normalized_segments))

    return normalized_segments


def merge_short_utterances(
    segments: List[Dict[str, Any]],
    min_duration_ms: int = 1000,
    logger: Optional["TalkSmithLogger"] = None,
) -> List[Dict[str, Any]]:
    """
    Merge consecutive utterances from the same speaker if they are too short.

    Args:
        segments: List of segment dictionaries
        min_duration_ms: Minimum duration in milliseconds for standalone utterance
        logger: Optional logger instance

    Returns:
        List of segments with short utterances merged
    """
    if not segments or min_duration_ms <= 0:
        return segments

    min_duration_sec = min_duration_ms / 1000.0
    merged_segments = []
    current_segment = None
    merge_count = 0

    for segment in segments:
        duration = segment["end"] - segment["start"]
        speaker = segment.get("speaker", "")
        gap = segment["start"] - current_segment["end"] if current_segment else 0.0

        if current_segment is None:
            # First segment
            current_segment = segment.copy()
        elif (
            speaker == current_segment.get("speaker", "")
            and gap < 2.0  # Only merge if gap is reasonable
            and (duration < min_duration_sec or gap < 1.0)
        ):
            # Merge short utterance with current segment OR same speaker with small gap
            current_segment["end"] = segment["end"]
            current_segment["text"] = (
                current_segment["text"].strip() + " " + segment["text"].strip()
            )
            if "words" in segment and "words" in current_segment:
                current_segment["words"].extend(segment["words"])
            merge_count += 1
        else:
            # Different speaker, large gap, or long standalone utterance - save and start new
            merged_segments.append(current_segment)
            current_segment = segment.copy()

    # Add the last segment
    if current_segment is not None:
        merged_segments.append(current_segment)

    if logger:
        logger.info(
            f"Merged {merge_count} short utterances",
            original_count=len(segments),
            merged_count=len(merged_segments),
            min_duration_ms=min_duration_ms,
        )

    return merged_segments


def postprocess_speakers(
    segments: List[Dict[str, Any]],
    normalize_names: bool = True,
    speaker_prefix: str = "Speaker",
    min_utterance_ms: Optional[int] = None,
    logger: Optional["TalkSmithLogger"] = None,
) -> List[Dict[str, Any]]:
    """
    Apply all speaker post-processing steps.

    Args:
        segments: List of segment dictionaries
        normalize_names: Whether to normalize speaker names
        speaker_prefix: Prefix for normalized speaker names
        min_utterance_ms: Minimum utterance duration in ms (None to skip merging)
        logger: Optional logger instance

    Returns:
        Post-processed segments
    """
    processed = segments

    if logger:
        logger.info(
            "Starting speaker post-processing",
            segment_count=len(segments),
            normalize_names=normalize_names,
            min_utterance_ms=min_utterance_ms,
        )

    # Step 1: Merge short utterances (before normalization to preserve original IDs)
    if min_utterance_ms is not None and min_utterance_ms > 0:
        processed = merge_short_utterances(processed, min_utterance_ms, logger)

    # Step 2: Normalize speaker names
    if normalize_names:
        processed = normalize_speaker_names(processed, speaker_prefix, logger)

    if logger:
        logger.info("Speaker post-processing complete", final_segment_count=len(processed))

    return processed


def main():
    """CLI entry point for speaker post-processing."""
    parser = argparse.ArgumentParser(
        description="Post-process speaker labels in transcription segments"
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Input JSON file with segments",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output JSON file (default: input_file with '_processed' suffix)",
    )
    parser.add_argument(
        "--normalize-names",
        action="store_true",
        default=True,
        help="Normalize speaker names to Speaker 1, Speaker 2, etc. (default: True)",
    )
    parser.add_argument(
        "--no-normalize-names",
        action="store_false",
        dest="normalize_names",
        help="Keep original speaker labels",
    )
    parser.add_argument(
        "--speaker-prefix",
        type=str,
        default="Speaker",
        help="Prefix for normalized speaker names (default: Speaker)",
    )
    parser.add_argument(
        "--min-utterance-ms",
        type=int,
        default=1000,
        help="Merge utterances shorter than this duration in milliseconds "
        "(default: 1000, 0 to disable)",
    )

    args = parser.parse_args()

    # Read input segments
    input_file = Path(args.input_file)
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return 1

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        segments = data.get("segments", [])

    # Process segments
    processed = postprocess_speakers(
        segments,
        normalize_names=args.normalize_names,
        speaker_prefix=args.speaker_prefix,
        min_utterance_ms=args.min_utterance_ms if args.min_utterance_ms > 0 else None,
    )

    # Determine output file
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = input_file.parent / f"{input_file.stem}_processed.json"

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"segments": processed}, f, indent=2, ensure_ascii=False)

    print(f"Processed {len(segments)} segments -> {len(processed)} segments")
    print(f"Output written to: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
