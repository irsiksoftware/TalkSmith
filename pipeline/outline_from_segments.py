"""Generate timestamped outline from transcription segments."""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pipeline.logger import TalkSmithLogger


def format_timestamp_anchor(seconds: float) -> str:
    """Format timestamp as [HH:MM:SS] anchor for outline."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"


def extract_key_phrases(text: str, max_words: int = 10) -> str:
    """
    Extract key phrases from text for outline entry.

    Args:
        text: Full text to extract from
        max_words: Maximum words to include

    Returns:
        Shortened text suitable for outline
    """
    words = text.strip().split()
    if len(words) <= max_words:
        return text.strip()

    # Take first max_words and add ellipsis
    return " ".join(words[:max_words]) + "..."


def detect_topic_change(
    prev_segment: Optional[Dict[str, Any]],
    curr_segment: Dict[str, Any],
    gap_threshold: float = 3.0,
) -> bool:
    """
    Detect if there's a topic change between segments.

    Args:
        prev_segment: Previous segment
        curr_segment: Current segment
        gap_threshold: Silence gap in seconds to consider topic change

    Returns:
        True if likely topic change
    """
    if prev_segment is None:
        return True

    # Speaker change indicates potential topic change
    if prev_segment.get("speaker") != curr_segment.get("speaker"):
        # If there's also a significant gap, it's likely a topic change
        gap = curr_segment["start"] - prev_segment["end"]
        if gap >= gap_threshold:
            return True

    # Long silence gap indicates topic change
    gap = curr_segment["start"] - prev_segment["end"]
    if gap >= gap_threshold * 2:  # Longer threshold for same speaker
        return True

    return False


def generate_outline(
    segments: List[Dict[str, Any]],
    interval_seconds: Optional[float] = 60.0,
    auto_detect_topics: bool = True,
    gap_threshold: float = 3.0,
    max_summary_words: int = 15,
    logger: Optional["TalkSmithLogger"] = None,
) -> List[Dict[str, Any]]:
    """
    Generate outline entries from segments.

    Args:
        segments: List of segment dictionaries
        interval_seconds: Generate entry every N seconds (None for auto-detect only)
        auto_detect_topics: Automatically detect topic changes
        gap_threshold: Silence gap threshold for topic detection (seconds)
        max_summary_words: Maximum words in summary text
        logger: Optional logger instance

    Returns:
        List of outline entries with timestamp, speaker, and summary
    """
    if not segments:
        return []

    if logger:
        logger.info(
            "Generating outline",
            segment_count=len(segments),
            interval_seconds=interval_seconds,
            auto_detect_topics=auto_detect_topics,
        )

    outline_entries = []
    last_outline_time = 0.0
    current_chunk = []
    prev_segment = None

    for segment in segments:
        # Check for topic change or time interval
        is_topic_change = False
        if auto_detect_topics:
            is_topic_change = detect_topic_change(prev_segment, segment, gap_threshold)

        time_for_entry = (
            interval_seconds is not None
            and segment["start"] - last_outline_time >= interval_seconds
        )

        if (is_topic_change or time_for_entry) and current_chunk:
            # Create outline entry from accumulated chunk
            chunk_start = current_chunk[0]["start"]
            chunk_speaker = current_chunk[0].get("speaker", "Unknown")
            chunk_text = " ".join(s["text"].strip() for s in current_chunk)
            summary = extract_key_phrases(chunk_text, max_summary_words)

            outline_entries.append({
                "timestamp": chunk_start,
                "timestamp_formatted": format_timestamp_anchor(chunk_start),
                "speaker": chunk_speaker,
                "summary": summary,
            })

            last_outline_time = chunk_start
            current_chunk = []

        # Add segment to current chunk
        current_chunk.append(segment)
        prev_segment = segment

    # Add final chunk if any
    if current_chunk:
        chunk_start = current_chunk[0]["start"]
        chunk_speaker = current_chunk[0].get("speaker", "Unknown")
        chunk_text = " ".join(s["text"].strip() for s in current_chunk)
        summary = extract_key_phrases(chunk_text, max_summary_words)

        outline_entries.append({
            "timestamp": chunk_start,
            "timestamp_formatted": format_timestamp_anchor(chunk_start),
            "speaker": chunk_speaker,
            "summary": summary,
        })

    if logger:
        logger.info(
            f"Generated outline with {len(outline_entries)} entries",
            entry_count=len(outline_entries),
        )

    return outline_entries


def format_outline_markdown(
    outline_entries: List[Dict[str, Any]],
    title: str = "Transcript Outline",
) -> str:
    """
    Format outline entries as Markdown.

    Args:
        outline_entries: List of outline entry dictionaries
        title: Title for the outline document

    Returns:
        Markdown formatted outline
    """
    lines = [f"# {title}", ""]

    for entry in outline_entries:
        timestamp = entry["timestamp_formatted"]
        speaker = entry["speaker"]
        summary = entry["summary"]
        lines.append(f"## {timestamp} {speaker}")
        lines.append(f"{summary}")
        lines.append("")

    return "\n".join(lines)


def generate_outline_from_file(
    input_file: Path,
    output_file: Optional[Path] = None,
    interval_seconds: Optional[float] = 60.0,
    auto_detect_topics: bool = True,
    gap_threshold: float = 3.0,
    title: Optional[str] = None,
    logger: Optional["TalkSmithLogger"] = None,
) -> Path:
    """
    Generate outline from segments file and write to Markdown.

    Args:
        input_file: Path to JSON file with segments
        output_file: Path to output Markdown file
        interval_seconds: Time interval for outline entries
        auto_detect_topics: Auto-detect topic changes
        gap_threshold: Silence gap threshold for topics
        title: Title for outline document
        logger: Optional logger instance

    Returns:
        Path to output file
    """
    # Read segments
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        segments = data.get("segments", [])

    # Generate outline
    outline_entries = generate_outline(
        segments,
        interval_seconds=interval_seconds,
        auto_detect_topics=auto_detect_topics,
        gap_threshold=gap_threshold,
        logger=logger,
    )

    # Format as Markdown
    if title is None:
        title = f"Outline: {input_file.stem}"
    markdown = format_outline_markdown(outline_entries, title)

    # Determine output file
    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}_outline.md"

    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)

    if logger:
        logger.info(f"Outline written to {output_file}", output_file=str(output_file))

    return output_file


def main():
    """CLI entry point for outline generation."""
    parser = argparse.ArgumentParser(
        description="Generate timestamped outline from transcription segments"
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
        help="Output Markdown file (default: input_file with '_outline.md' suffix)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Time interval in seconds for outline entries (default: 60, 0 to disable)",
    )
    parser.add_argument(
        "--no-auto-detect",
        action="store_false",
        dest="auto_detect",
        help="Disable automatic topic change detection",
    )
    parser.add_argument(
        "--gap-threshold",
        type=float,
        default=3.0,
        help="Silence gap threshold in seconds for topic detection (default: 3.0)",
    )
    parser.add_argument(
        "--title",
        type=str,
        help="Title for outline document (default: based on filename)",
    )

    args = parser.parse_args()

    # Validate input
    input_file = Path(args.input_file)
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return 1

    # Generate outline
    interval = args.interval if args.interval > 0 else None
    output_file = generate_outline_from_file(
        input_file,
        output_file=args.output,
        interval_seconds=interval,
        auto_detect_topics=args.auto_detect,
        gap_threshold=args.gap_threshold,
        title=args.title,
    )

    print(f"Outline generated: {output_file}")

    return 0


if __name__ == "__main__":
    exit(main())
