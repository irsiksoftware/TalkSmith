"""
TalkSmith CLI - Unified command-line interface for transcription pipeline.

Provides subcommands for:
- transcribe: Transcribe audio files
- preprocess: Preprocess audio for better quality
- diarize: Speaker diarization
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
    - Multi-GPU parallel processing support
    """
    # Check if multi-GPU mode is requested
    if args.multi_gpu:
        # Delegate to launcher_multigpu.py
        import subprocess

        launcher_path = Path(__file__).parent.parent / "launcher_multigpu.py"
        if not launcher_path.exists():
            print(f"ERROR: launcher_multigpu.py not found at {launcher_path}")
            return 1

        cmd = [
            sys.executable,
            str(launcher_path),
            "--input-dir",
            args.input_dir,
            "--output-dir",
            args.output_dir,
        ]

        if args.gpus:
            cmd.extend(["--gpus", args.gpus])
        else:
            cmd.extend(["--gpus", "auto"])

        if args.model_size:
            cmd.extend(["--model-size", args.model_size])

        if args.language:
            cmd.extend(["--language", args.language])

        if args.pattern:
            cmd.extend(["--pattern", args.pattern])

        print(f"Launching multi-GPU transcription: {' '.join(cmd)}\n")
        result = subprocess.run(cmd)
        return result.returncode

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


def transcribe_command(args: argparse.Namespace) -> int:
    """
    Transcribe audio file with optional diarization.

    Demonstrates:
    - Integration with transcribe_fw.py
    - Optional diarization integration
    - Automatic export to multiple formats
    - Structured logging
    """
    # Lazy import to avoid import errors when dependencies not installed
    from pipeline.transcribe_fw import transcribe_file

    input_path = Path(args.input)

    # Create slug for logging
    slug = create_slug_from_filename(input_path.name)
    logger = get_logger(__name__, slug=slug)

    logger.log_start(
        "transcribe",
        input_file=str(input_path),
        model=args.model,
        diarize=args.diarize,
    )

    try:
        # Check input file exists
        if not input_path.exists():
            exit_code = logger.log_error_exit(
                f"Input file not found: {input_path}", file=str(input_path)
            )
            return exit_code

        # Set output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Optional preprocessing
        audio_path_for_transcription = input_path
        if args.preprocess or args.denoise or args.loudnorm or args.trim_silence:
            from pipeline.preprocess import preprocess_audio

            logger.info(
                "Preprocessing audio before transcription",
                denoise=args.denoise or args.preprocess,
                loudnorm=args.loudnorm or args.preprocess,
                trim_silence=args.trim_silence or args.preprocess,
            )

            preprocessed_path = output_dir / f"{input_path.stem}_preprocessed.wav"
            preprocessed_path, preprocess_metrics = preprocess_audio(
                input_path=input_path,
                output_path=preprocessed_path,
                denoise=args.denoise or args.preprocess,
                loudnorm=args.loudnorm or args.preprocess,
                trim_silence=args.trim_silence or args.preprocess,
            )

            logger.log_metrics(preprocess_metrics)
            logger.info(f"Preprocessing complete: {preprocessed_path}")
            audio_path_for_transcription = preprocessed_path

        # Transcribe audio
        logger.info(
            f"Transcribing with {args.model} model",
            model=args.model,
            device=args.device,
        )

        result = transcribe_file(
            audio_path=str(audio_path_for_transcription),
            output_dir=str(output_dir),
            model_size=args.model,
            device=args.device,
            language=args.language,
        )

        logger.log_metrics(
            {
                "duration": result["duration"],
                "processing_time": result["processing_time"],
                "rtf": result["rtf"],
                "language": result["language"],
                "language_probability": result["language_probability"],
            }
        )

        # Optional diarization
        if args.diarize:
            from pipeline.diarize_alt import diarize_file

            logger.info("Running speaker diarization")

            # Get transcript JSON path (use original filename for consistency)
            transcript_json = output_dir / f"{input_path.stem}.json"

            # Run diarization (use preprocessed audio if available)
            diarized_json = output_dir / f"{input_path.stem}_diarized.json"
            diarize_file(
                audio_path=str(audio_path_for_transcription),
                output_path=str(diarized_json),
                num_speakers=args.num_speakers,
                transcript_path=str(transcript_json),
            )

            logger.info("Diarization complete", output=str(diarized_json))

            # Load diarized segments for export
            with open(diarized_json, "r", encoding="utf-8") as f:
                diarized_data = json.load(f)
                segments = diarized_data.get("segments", [])
        else:
            segments = result["segments"]

        # Auto-export to formats
        if args.formats:
            formats = args.formats.split(",")
            base_name = input_path.stem

            logger.info("Exporting to formats", formats=formats)

            output_files = export_all(
                segments=segments,
                output_dir=output_dir,
                base_name=base_name,
                formats=formats,
            )

            print(f"\nExported to:")
            for fmt, path in output_files.items():
                print(f"  {fmt.upper()}: {path}")

        logger.log_complete("transcribe")

        print(f"\nTranscription complete!")
        print(f"Duration: {result['duration']:.2f}s")
        print(f"Processing time: {result['processing_time']:.2f}s")
        print(f"RTF: {result['rtf']:.3f}")
        print(
            f"Language: {result['language']} " f"({result['language_probability']:.2%})"
        )

        return 0

    except Exception as e:
        logger.exception("Transcription failed", error=str(e))
        print(f"ERROR: {e}")
        return 1


def preprocess_command(args: argparse.Namespace) -> int:
    """
    Preprocess audio file for better transcription quality.

    Demonstrates:
    - Integration with preprocess.py
    - Audio quality improvement options
    - Metrics logging
    """
    # Lazy import to avoid import errors when dependencies not installed
    from pipeline.preprocess import preprocess_audio

    input_path = Path(args.input)

    # Create slug for logging
    slug = create_slug_from_filename(input_path.name)
    logger = get_logger(__name__, slug=slug)

    logger.log_start(
        "preprocess",
        input_file=str(input_path),
        denoise=args.denoise,
        trim=args.trim,
    )

    try:
        # Check input file exists
        if not input_path.exists():
            exit_code = logger.log_error_exit(
                f"Input file not found: {input_path}", file=str(input_path)
            )
            return exit_code

        # Set output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.parent / f"{input_path.stem}_preprocessed.wav"

        # Preprocess audio
        logger.info(
            "Preprocessing audio",
            denoise=args.denoise,
            loudnorm=args.loudnorm,
            trim_silence=args.trim,
        )

        output_path, metrics = preprocess_audio(
            input_path=input_path,
            output_path=output_path,
            denoise=args.denoise,
            loudnorm=args.loudnorm,
            trim_silence=args.trim,
            silence_threshold_db=args.silence_threshold,
            high_pass_filter=args.high_pass_filter,
        )

        logger.log_metrics(metrics)
        logger.log_complete("preprocess", output_file=str(output_path))

        print(f"\nPreprocessed audio saved to: {output_path}")
        print("\nMetrics:")
        print(f"  Original duration: {metrics['original_duration_seconds']:.2f}s")
        print(f"  Final duration: {metrics['final_duration_seconds']:.2f}s")
        print(f"  Steps applied: {', '.join(metrics['steps_applied'])}")

        return 0

    except Exception as e:
        logger.exception("Preprocessing failed", error=str(e))
        print(f"ERROR: {e}")
        return 1


def diarize_command(args: argparse.Namespace) -> int:
    """
    Perform speaker diarization on audio file.

    Demonstrates:
    - Integration with diarize_alt.py
    - Speaker detection and labeling
    - Optional transcript alignment
    """
    # Lazy import to avoid import errors when dependencies not installed
    from pipeline.diarize_alt import diarize_file

    input_path = Path(args.input)

    # Create slug for logging
    slug = create_slug_from_filename(input_path.name)
    logger = get_logger(__name__, slug=slug)

    logger.log_start(
        "diarize",
        input_file=str(input_path),
        num_speakers=args.num_speakers,
    )

    try:
        # Check input file exists
        if not input_path.exists():
            exit_code = logger.log_error_exit(
                f"Input file not found: {input_path}", file=str(input_path)
            )
            return exit_code

        # Set output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = input_path.parent / f"{input_path.stem}_diarized.json"

        # Run diarization
        logger.info(
            "Running speaker diarization",
            num_speakers=args.num_speakers or "auto",
        )

        segments = diarize_file(
            audio_path=str(input_path),
            output_path=str(output_path),
            num_speakers=args.num_speakers,
            transcript_path=args.transcript,
            window_size=args.window_size,
        )

        num_speakers = len(set(seg["speaker"] for seg in segments))

        logger.log_metrics(
            {
                "num_speakers": num_speakers,
                "num_segments": len(segments),
            }
        )

        logger.log_complete("diarize", output_file=str(output_path))

        print(f"\nDiarization complete!")
        print(f"Speakers detected: {num_speakers}")
        print(f"Segments created: {len(segments)}")
        print(f"Output: {output_path}")

        return 0

    except Exception as e:
        logger.exception("Diarization failed", error=str(e))
        print(f"ERROR: {e}")
        return 1


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

    # Transcribe command
    transcribe_parser = subparsers.add_parser(
        "transcribe", help="Transcribe audio file"
    )
    transcribe_parser.add_argument("input", help="Input audio file")
    transcribe_parser.add_argument(
        "-o",
        "--output-dir",
        default="data/outputs",
        help="Output directory (default: data/outputs)",
    )
    transcribe_parser.add_argument(
        "-m",
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "medium.en", "large-v3"],
        help="Whisper model size (default: base)",
    )
    transcribe_parser.add_argument(
        "--device",
        default="cuda",
        choices=["cuda", "cpu"],
        help="Device to use (default: cuda)",
    )
    transcribe_parser.add_argument(
        "-l",
        "--language",
        help="Language code (e.g., 'en'). Auto-detect if not specified.",
    )
    transcribe_parser.add_argument(
        "--diarize",
        action="store_true",
        help="Enable speaker diarization",
    )
    transcribe_parser.add_argument(
        "--num-speakers",
        type=int,
        help="Number of speakers for diarization (auto-detect if not specified)",
    )
    transcribe_parser.add_argument(
        "-f",
        "--formats",
        help="Comma-separated export formats: txt,srt,vtt,json (e.g., 'txt,srt')",
    )
    # Preprocessing options
    transcribe_parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Enable audio preprocessing before transcription",
    )
    transcribe_parser.add_argument(
        "--denoise",
        action="store_true",
        help="Enable noise reduction during preprocessing",
    )
    transcribe_parser.add_argument(
        "--loudnorm",
        action="store_true",
        help="Enable loudness normalization during preprocessing",
    )
    transcribe_parser.add_argument(
        "--trim-silence",
        action="store_true",
        help="Trim silence during preprocessing",
    )

    # Preprocess command
    preprocess_parser = subparsers.add_parser(
        "preprocess", help="Preprocess audio for better quality"
    )
    preprocess_parser.add_argument("input", help="Input audio file")
    preprocess_parser.add_argument(
        "-o",
        "--output",
        help="Output file (default: <input>_preprocessed.wav)",
    )
    preprocess_parser.add_argument(
        "--denoise",
        action="store_true",
        help="Enable denoising",
    )
    preprocess_parser.add_argument(
        "--loudnorm",
        action="store_true",
        help="Enable loudness normalization",
    )
    preprocess_parser.add_argument(
        "--trim",
        action="store_true",
        help="Trim silence from audio",
    )
    preprocess_parser.add_argument(
        "--silence-threshold",
        type=float,
        default=-40.0,
        help="Silence threshold in dB (default: -40)",
    )
    preprocess_parser.add_argument(
        "--high-pass-filter",
        action="store_true",
        help="Enable high-pass filter",
    )

    # Diarize command
    diarize_parser = subparsers.add_parser(
        "diarize", help="Perform speaker diarization"
    )
    diarize_parser.add_argument("input", help="Input audio file")
    diarize_parser.add_argument(
        "-o",
        "--output",
        help="Output JSON path (default: <input>_diarized.json)",
    )
    diarize_parser.add_argument(
        "--num-speakers",
        type=int,
        help="Number of speakers (default: auto-detect)",
    )
    diarize_parser.add_argument(
        "--transcript",
        help="Path to transcript JSON for alignment",
    )
    diarize_parser.add_argument(
        "--window-size",
        type=float,
        default=1.5,
        help="Window size in seconds (default: 1.5)",
    )

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
    batch_parser.add_argument(
        "--multi-gpu",
        action="store_true",
        help="Enable multi-GPU processing (requires launcher_multigpu.py)",
    )
    batch_parser.add_argument(
        "--gpus",
        help="Comma-separated GPU IDs for multi-GPU mode (e.g., '0,1,2') or 'auto'",
    )
    batch_parser.add_argument(
        "--model-size",
        default="base",
        help="Model size for transcription in multi-GPU mode (default: base)",
    )
    batch_parser.add_argument(
        "--language",
        help="Language code for transcription in multi-GPU mode (e.g., 'en')",
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
    if args.command == "transcribe":
        return transcribe_command(args)
    elif args.command == "preprocess":
        return preprocess_command(args)
    elif args.command == "diarize":
        return diarize_command(args)
    elif args.command == "export":
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
