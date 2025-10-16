"""
TalkSmith CLI - Unified command-line interface for transcription pipeline.

Provides subcommands for:
- export: Export segments to various formats
- batch: Batch process multiple files
- demo: Demonstrate logging and error handling
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.logger import (
    get_logger,
    BatchLogSummary,
    with_retry,
    TransientError,
)
from pipeline.exporters import export_all
from config.settings import get_config


def create_slug_from_filename(filename: str) -> str:
    """Create a slug from a filename for logging."""
    # Remove extension and sanitize
    slug = Path(filename).stem
    slug = slug.replace(" ", "-").replace("_", "-")
    return slug.lower()


def export_command(args: argparse.Namespace) -> int:
    """Export segments to various formats with logging."""
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    # Create slug for logging
    slug = create_slug_from_filename(input_path.name)
    logger = get_logger(__name__, slug=slug)

    logger.log_start("export", input_file=str(input_path), formats=args.formats)

    try:
        # Load segments from JSON
        if not input_path.exists():
            exit_code = logger.log_error_exit(
                f"Input file not found: {input_path}", file=str(input_path)
            )
            return exit_code

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            segments = data.get("segments", [])

        logger.info(f"Loaded {len(segments)} segments", segment_count=len(segments))

        # Export to formats
        formats = (
            args.formats.split(",") if args.formats else ["txt", "srt", "vtt", "json"]
        )
        base_name = args.name or input_path.stem

        logger.info("Exporting to formats", formats=formats, base_name=base_name)

        output_files = export_all(
            segments=segments,
            output_dir=output_dir,
            base_name=base_name,
            formats=formats,
        )

        logger.log_complete(
            "export",
            output_files={fmt: str(path) for fmt, path in output_files.items()},
        )

        # Print output paths for user
        print(f"\nExported {len(segments)} segments to:")
        for fmt, path in output_files.items():
            print(f"  {fmt.upper()}: {path}")

        return 0

    except Exception as e:
        logger.exception("Export failed", error=str(e))
        return 1


def batch_command(args: argparse.Namespace) -> int:
    """
    Batch process multiple segment files with logging and error handling.

    Demonstrates:
    - BatchLogSummary for tracking successes/failures
    - Proper exit code handling
    - Per-file logging
    """
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    # Create batch logger
    logger = get_logger(__name__, slug="batch-export")
    batch_summary = BatchLogSummary(logger)

    logger.log_start("batch_export", input_dir=str(input_dir))

    # Find all JSON files
    pattern = args.pattern or "*.json"
    json_files = list(input_dir.glob(pattern))

    if not json_files:
        logger.warning(f"No files found matching pattern: {pattern}", pattern=pattern)
        print(f"No files found in {input_dir} matching {pattern}")
        return 0

    logger.info(f"Found {len(json_files)} files to process", file_count=len(json_files))

    formats = args.formats.split(",") if args.formats else ["txt", "srt", "vtt", "json"]

    # Process each file
    for json_file in json_files:
        file_slug = create_slug_from_filename(json_file.name)
        file_logger = get_logger(__name__, slug=file_slug)

        try:
            file_logger.log_start("export", input_file=str(json_file))

            # Load segments
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                segments = data.get("segments", [])

            if not segments:
                file_logger.warning("No segments found in file")
                batch_summary.record_failure(str(json_file), "No segments in file")
                continue

            # Export
            output_files = export_all(
                segments=segments,
                output_dir=output_dir / json_file.stem,
                base_name=json_file.stem,
                formats=formats,
            )

            file_logger.log_complete(
                "export",
                segment_count=len(segments),
                output_files={fmt: str(path) for fmt, path in output_files.items()},
            )

            batch_summary.record_success(str(json_file))

        except Exception as e:
            file_logger.exception(f"Failed to process {json_file}", error=str(e))
            batch_summary.record_failure(str(json_file), str(e))

    # Print summary
    batch_summary.print_summary()
    logger.log_complete("batch_export", total=batch_summary.total)

    print(f"\nBatch processing complete:")
    print(f"  Total: {batch_summary.total}")
    print(f"  Successful: {batch_summary.successful}")
    print(f"  Failed: {batch_summary.failed}")

    if batch_summary.errors:
        print(f"\nFailed files:")
        for error in batch_summary.errors:
            print(f"  - {error['item']}: {error['error']}")

    return batch_summary.get_exit_code()


def demo_command(args: argparse.Namespace) -> int:
    """
    Demonstrate logging features including retry/backoff.

    Shows:
    - Structured logging with custom fields
    - Metrics logging
    - Retry decorator with transient errors
    - Error handling and exit codes
    """
    logger = get_logger(__name__, slug="demo")

    print("=== TalkSmith Logging Demo ===\n")

    # 1. Basic logging
    print("1. Basic structured logging:")
    logger.info("Demo started", demo_type=args.demo_type or "full")
    logger.log_start("demo_operation", param1="value1", param2="value2")

    # 2. Metrics logging
    print("2. Metrics logging:")
    logger.log_metrics(
        {
            "rtf": 0.12,
            "duration_seconds": 3600,
            "model": "large-v3",
            "gpu_memory_mb": 8192,
        }
    )

    # 3. Retry with transient errors
    print("3. Retry mechanism with exponential backoff:")

    attempt_count = {"count": 0}

    @with_retry(max_attempts=3, initial_delay=0.5, backoff_factor=2.0, logger=logger)
    def simulated_api_call():
        """Simulate an API call that fails twice then succeeds."""
        attempt_count["count"] += 1
        print(f"   Attempt {attempt_count['count']}...")

        if attempt_count["count"] < 3:
            raise TransientError(
                f"Simulated transient failure (attempt {attempt_count['count']})"
            )

        return {"status": "success", "data": "result"}

    try:
        result = simulated_api_call()
        logger.info(
            "API call succeeded", result=result, total_attempts=attempt_count["count"]
        )
        print(f"   [OK] Success after {attempt_count['count']} attempts")
    except TransientError as e:
        logger.error("API call failed after all retries", error=str(e))
        print(f"   [FAIL] Failed after {attempt_count['count']} attempts")

    # 4. Batch summary demo
    print("\n4. Batch operation summary:")
    batch = BatchLogSummary(logger)
    batch.record_success("file1.wav")
    batch.record_success("file2.wav")
    batch.record_success("file3.wav")
    batch.record_failure("file4.wav", "File not found")
    batch.record_failure("file5.wav", "Corrupted audio")
    batch.print_summary()

    print(
        f"   Total: {batch.total}, Success: {batch.successful}, Failed: {batch.failed}"
    )
    print(f"   Exit code would be: {batch.get_exit_code()}")

    # 5. Complete operation
    logger.log_complete("demo_operation", duration_seconds=2.5)

    print("\n[OK] Demo complete! Check logs at: data/outputs/demo/logs/demo.log")
    print(f"  (if configured with slug-based logging)")

    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="TalkSmith - Local GPU-accelerated transcription pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Export command
    export_parser = subparsers.add_parser(
        "export", help="Export segments to various formats"
    )
    export_parser.add_argument("input", help="Input JSON file with segments")
    export_parser.add_argument(
        "-o",
        "--output-dir",
        default="data/outputs",
        help="Output directory (default: data/outputs)",
    )
    export_parser.add_argument(
        "-f",
        "--formats",
        help="Comma-separated list of formats: txt,srt,vtt,json (default: all)",
    )
    export_parser.add_argument(
        "-n", "--name", help="Base name for output files (default: input filename)"
    )

    # Batch command
    batch_parser = subparsers.add_parser(
        "batch", help="Batch export multiple segment files"
    )
    batch_parser.add_argument(
        "input_dir", help="Input directory containing JSON segment files"
    )
    batch_parser.add_argument(
        "-o",
        "--output-dir",
        default="data/outputs",
        help="Output directory (default: data/outputs)",
    )
    batch_parser.add_argument(
        "-p",
        "--pattern",
        default="*.json",
        help="File pattern to match (default: *.json)",
    )
    batch_parser.add_argument(
        "-f",
        "--formats",
        help="Comma-separated list of formats (default: txt,srt,vtt,json)",
    )

    # Demo command
    demo_parser = subparsers.add_parser(
        "demo", help="Demonstrate logging and error handling features"
    )
    demo_parser.add_argument(
        "-t", "--demo-type", help="Type of demo to run (optional metadata)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Route to appropriate command
    if args.command == "export":
        return export_command(args)
    elif args.command == "batch":
        return batch_command(args)
    elif args.command == "demo":
        return demo_command(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
