#!/usr/bin/env python3
"""
TalkSmith CLI - Unified command-line interface for audio transcription pipeline.

Usage:
    python cli/main.py transcribe --input audio.wav [options]
    python cli/main.py diarize --input audio.wav [options]
    python cli/main.py batch --input-dir ./recordings [options]
    python cli/main.py export --input segments.json --format srt,vtt [options]
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.logger import BatchLogSummary, get_logger  # noqa: E402


def setup_parser() -> argparse.ArgumentParser:
    """
    Set up the argument parser with all subcommands.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="talksmith",
        description="TalkSmith - Local GPU-accelerated transcription and diarization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Transcribe a single file
  python cli/main.py transcribe --input audio.wav --model large-v3

  # Transcribe with diarization
  python cli/main.py diarize --input audio.wav --speakers 2-5

  # Batch process a directory
  python cli/main.py batch --input-dir ./recordings --diarize

  # Export to multiple formats
  python cli/main.py export --input segments.json --format srt,vtt,txt

For more information, visit: https://github.com/DakotaIrsik/TalkSmith
        """,
    )

    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    parser.add_argument("--config", type=str, help="Path to custom settings.ini file")

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress all output except errors"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Transcribe command
    transcribe_parser = subparsers.add_parser(
        "transcribe", help="Transcribe a single audio file"
    )
    transcribe_parser.add_argument(
        "--input", "-i", required=True, type=str, help="Input audio file path"
    )
    transcribe_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output directory (default: data/outputs/<slug>)",
    )
    transcribe_parser.add_argument(
        "--model",
        type=str,
        help="Whisper model size (tiny, base, small, medium, large-v3)",
    )
    transcribe_parser.add_argument(
        "--language", type=str, help="Language code (e.g., en, es, fr)"
    )
    transcribe_parser.add_argument(
        "--device",
        type=str,
        choices=["cuda", "cpu"],
        help="Device to use (cuda or cpu)",
    )

    # Diarize command
    diarize_parser = subparsers.add_parser(
        "diarize", help="Transcribe with speaker diarization"
    )
    diarize_parser.add_argument(
        "--input", "-i", required=True, type=str, help="Input audio file path"
    )
    diarize_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output directory (default: data/outputs/<slug>)",
    )
    diarize_parser.add_argument("--model", type=str, help="Whisper model size")
    diarize_parser.add_argument(
        "--speakers", type=str, help='Expected speaker count (e.g., "2" or "2-5")'
    )
    diarize_parser.add_argument(
        "--hf-token", type=str, help="HuggingFace token for pyannote models"
    )

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Process multiple audio files")
    batch_parser.add_argument(
        "--input-dir",
        required=True,
        type=str,
        help="Input directory containing audio files",
    )
    batch_parser.add_argument(
        "--output-dir", type=str, help="Output directory (default: data/outputs)"
    )
    batch_parser.add_argument(
        "--pattern",
        type=str,
        default="*.wav",
        help="File pattern to match (default: *.wav)",
    )
    batch_parser.add_argument(
        "--diarize", action="store_true", help="Enable speaker diarization"
    )
    batch_parser.add_argument("--model", type=str, help="Whisper model size")
    batch_parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous run (skip completed files)",
    )

    # Export command
    export_parser = subparsers.add_parser(
        "export", help="Export segments to various formats"
    )
    export_parser.add_argument(
        "--input", "-i", required=True, type=str, help="Input segments JSON file"
    )
    export_parser.add_argument(
        "--output-dir", "-o", type=str, help="Output directory (default: same as input)"
    )
    export_parser.add_argument(
        "--format",
        "-f",
        type=str,
        default="txt,json,srt",
        help="Export formats (comma-separated: txt,json,srt,vtt)",
    )

    # Plan command (optional)
    plan_parser = subparsers.add_parser(
        "plan", help="Generate outline/plan from transcript"
    )
    plan_parser.add_argument(
        "--input", "-i", required=True, type=str, help="Input segments JSON file"
    )
    plan_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (default: <input>_outline.md)",
    )

    return parser


def cmd_transcribe(args) -> int:
    """
    Execute transcribe command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger = get_logger(__name__)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return 1

    logger.info("Transcription not yet implemented")
    logger.info(f"Would transcribe: {input_path}")
    logger.info(f"Model: {args.model or 'default'}")

    return logger.log_error_exit(
        "Transcription pipeline not yet implemented. See issue #5", exit_code=1
    )


def cmd_diarize(args) -> int:
    """
    Execute diarize command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger = get_logger(__name__)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return 1

    logger.info("Diarization not yet implemented")
    logger.info(f"Would diarize: {input_path}")
    logger.info(f"Speakers: {args.speakers or 'auto-detect'}")

    return logger.log_error_exit(
        "Diarization pipeline not yet implemented. See issue #6", exit_code=1
    )


def cmd_batch(args) -> int:
    """
    Execute batch command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger = get_logger(__name__)
    batch_summary = BatchLogSummary(logger)

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return 1

    # Find matching files
    files = list(input_dir.glob(args.pattern))

    if not files:
        logger.warning(
            f"No files matching pattern '{args.pattern}' found in {input_dir}"
        )
        return 0

    logger.info(f"Found {len(files)} files to process")
    logger.info("Batch processing not yet fully implemented")

    # Simulate processing
    for audio_file in files:
        logger.info(f"Would process: {audio_file.name}")
        batch_summary.record_success(str(audio_file))

    batch_summary.print_summary()

    return logger.log_error_exit(
        "Batch processing pipeline not yet implemented. See issue #9", exit_code=1
    )


def cmd_export(args) -> int:
    """
    Execute export command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger = get_logger(__name__)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return 1

    # Load segments from JSON
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "segments" not in data:
            logger.error("Input JSON file must contain 'segments' key")
            return 1

        segments = data["segments"]
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        return 1
    except Exception as e:
        logger.error(f"Failed to load input file: {e}")
        return 1

    # Determine output directory
    output_dir = Path(args.output_dir) if args.output_dir else input_path.parent
    base_name = input_path.stem

    # Parse formats
    formats = [fmt.strip() for fmt in args.format.split(",")]

    # Export to requested formats
    try:
        from pipeline.exporters import export_all

        logger.info(
            f"Exporting {len(segments)} segments to formats: {', '.join(formats)}"
        )
        output_files = export_all(segments, output_dir, base_name, formats=formats)

        # Log success
        logger.info("Export completed successfully")
        for fmt, path in output_files.items():
            logger.info(f"  {fmt.upper()}: {path}")

        return 0

    except ValueError as e:
        logger.error(f"Export error: {e}")
        return 1
    except Exception:
        logger.exception("Unexpected error during export")
        return 1


def cmd_plan(args) -> int:
    """
    Execute plan command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger = get_logger(__name__)

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return 1

    logger.info("Plan generation not yet implemented")

    return logger.log_error_exit(
        "Plan generation not yet implemented. See issue #16", exit_code=1
    )


def main() -> int:
    """
    Main entry point for TalkSmith CLI.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = setup_parser()
    args = parser.parse_args()

    # Handle no command
    if not args.command:
        parser.print_help()
        return 0

    # Set up logging level
    if args.verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)
    elif args.quiet:
        import logging

        logging.basicConfig(level=logging.ERROR)

    # Load custom config if specified
    if args.config:
        # TODO: Implement custom config loading
        pass

    # Route to appropriate command handler
    command_handlers = {
        "transcribe": cmd_transcribe,
        "diarize": cmd_diarize,
        "batch": cmd_batch,
        "export": cmd_export,
        "plan": cmd_plan,
    }

    handler = command_handlers.get(args.command)
    if handler:
        try:
            return handler(args)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            return 130  # Standard exit code for Ctrl+C
        except Exception:
            logger = get_logger(__name__)
            logger.exception(f"Unexpected error in {args.command} command")
            return 1
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
