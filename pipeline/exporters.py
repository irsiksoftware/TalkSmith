"""Export transcription segments to various formats (TXT, SRT, VTT, JSON)."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from pipeline.logger import TalkSmithLogger


def format_timestamp_srt(seconds: float) -> str:
    """Format timestamp for SRT format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_timestamp_vtt(seconds: float) -> str:
    """Format timestamp for WebVTT format (HH:MM:SS.mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def validate_segments(segments: List[Dict[str, Any]]) -> None:
    """Validate segment data structure."""
    if not isinstance(segments, list):
        raise ValueError("Segments must be a list")
    for i, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise ValueError(f"Segment {i} must be a dictionary")
        if "start" not in segment or "end" not in segment:
            raise ValueError(f"Segment {i} missing 'start' or 'end' timestamp")
        if "text" not in segment:
            raise ValueError(f"Segment {i} missing 'text' field")
        start, end = segment["start"], segment["end"]
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            raise ValueError(f"Segment {i} timestamps must be numeric")
        if start < 0 or end < 0:
            raise ValueError(f"Segment {i} has negative timestamp")
        if start > end:
            raise ValueError(f"Segment {i} has start time after end time")


def export_txt(
    segments: List[Dict[str, Any]],
    output_path: Path,
    include_timestamps: bool = True,
    include_speakers: bool = True,
    logger: Optional["TalkSmithLogger"] = None,
) -> None:
    """Export segments to plain text format."""
    validate_segments(segments)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if logger:
        logger.debug(
            f"Exporting to TXT: {output_path}",
            format="txt",
            segment_count=len(segments),
        )

    with open(output_path, "w", encoding="utf-8") as f:
        for segment in segments:
            line_parts = []
            if include_timestamps:
                start_ts = format_timestamp_vtt(segment["start"])
                end_ts = format_timestamp_vtt(segment["end"])
                line_parts.append(f"[{start_ts} --> {end_ts}]")
            if include_speakers and "speaker" in segment:
                line_parts.append(f"{segment['speaker']}:")
            line_parts.append(segment["text"])
            f.write(" ".join(line_parts) + "\n")

    if logger:
        logger.debug(
            f"TXT export complete: {output_path}",
            format="txt",
            output_file=str(output_path),
        )


def export_srt(
    segments: List[Dict[str, Any]],
    output_path: Path,
    include_speakers: bool = True,
    logger: Optional["TalkSmithLogger"] = None,
) -> None:
    """Export segments to SRT subtitle format."""
    validate_segments(segments)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if logger:
        logger.debug(
            f"Exporting to SRT: {output_path}",
            format="srt",
            segment_count=len(segments),
        )

    with open(output_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, start=1):
            f.write(f"{i}\n")
            start_ts = format_timestamp_srt(segment["start"])
            end_ts = format_timestamp_srt(segment["end"])
            f.write(f"{start_ts} --> {end_ts}\n")
            text = (
                f"{segment['speaker']}: {segment['text']}"
                if include_speakers and "speaker" in segment
                else segment["text"]
            )
            f.write(f"{text}\n\n")

    if logger:
        logger.debug(
            f"SRT export complete: {output_path}",
            format="srt",
            output_file=str(output_path),
        )


def export_vtt(
    segments: List[Dict[str, Any]],
    output_path: Path,
    include_speakers: bool = True,
    logger: Optional["TalkSmithLogger"] = None,
) -> None:
    """Export segments to WebVTT subtitle format."""
    validate_segments(segments)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if logger:
        logger.debug(
            f"Exporting to VTT: {output_path}",
            format="vtt",
            segment_count=len(segments),
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for segment in segments:
            if include_speakers and "speaker" in segment:
                f.write(f"{segment['speaker']}\n")
            start_ts = format_timestamp_vtt(segment["start"])
            end_ts = format_timestamp_vtt(segment["end"])
            f.write(f"{start_ts} --> {end_ts}\n")
            f.write(f"{segment['text']}\n\n")

    if logger:
        logger.debug(
            f"VTT export complete: {output_path}",
            format="vtt",
            output_file=str(output_path),
        )


def export_json(
    segments: List[Dict[str, Any]],
    output_path: Path,
    pretty: bool = True,
    include_words: bool = True,
    logger: Optional["TalkSmithLogger"] = None,
) -> None:
    """Export segments to JSON format."""
    validate_segments(segments)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if logger:
        logger.debug(
            f"Exporting to JSON: {output_path}",
            format="json",
            segment_count=len(segments),
        )

    export_data = {"segments": []}
    for segment in segments:
        segment_data = {
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"],
        }
        if "speaker" in segment:
            segment_data["speaker"] = segment["speaker"]
        if include_words and "words" in segment:
            segment_data["words"] = segment["words"]
        export_data["segments"].append(segment_data)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2 if pretty else None, ensure_ascii=False)

    if logger:
        logger.debug(
            f"JSON export complete: {output_path}",
            format="json",
            output_file=str(output_path),
        )


def export_all(
    segments: List[Dict[str, Any]],
    output_dir: Path,
    base_name: str,
    formats: Optional[List[str]] = None,
    logger: Optional["TalkSmithLogger"] = None,
) -> Dict[str, Path]:
    """Export segments to multiple formats at once."""
    if formats is None:
        formats = ["txt", "srt", "vtt", "json"]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if logger:
        logger.info(f"Exporting to {len(formats)} formats", formats=formats, base_name=base_name)

    format_handlers = {
        "txt": (export_txt, ".txt"),
        "srt": (export_srt, ".srt"),
        "vtt": (export_vtt, ".vtt"),
        "json": (export_json, ".json"),
    }
    output_files = {}
    for fmt in formats:
        if fmt not in format_handlers:
            raise ValueError(f"Unknown format: {fmt}")
        handler, extension = format_handlers[fmt]
        output_path = output_dir / f"{base_name}{extension}"
        handler(segments, output_path, logger=logger)
        output_files[fmt] = output_path

    if logger:
        logger.info(
            f"Export complete: {len(output_files)} files created",
            output_count=len(output_files),
        )

    return output_files
