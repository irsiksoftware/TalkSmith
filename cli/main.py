#!/usr/bin/env python3
"""
TalkSmith CLI - Unified command-line interface for transcription and diarization.

Usage:
    talksmith transcribe [options] <input>
    talksmith diarize [options] <input>
    talksmith batch [options] <input-dir>
    talksmith preprocess [options] <input>
    talksmith export [options] <segments>
    talksmith plan [options] <segments>
    talksmith sync [options]
"""

import argparse
import sys
from pathlib import Path


def create_parser():
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="talksmith",
        description="Local GPU-accelerated transcription and diarization pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="TalkSmith 0.1.0",
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to settings.ini configuration file",
        metavar="FILE",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        required=True,
    )

    # Preprocess command
    preprocess_parser = subparsers.add_parser(
        "preprocess",
        help="Preprocess audio files (denoise, normalize, trim)",
    )
    preprocess_parser.add_argument(
        "input",
        type=str,
        help="Input audio file or directory",
    )
    preprocess_parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file or directory (default: data/outputs)",
    )
    preprocess_parser.add_argument(
        "--denoise",
        action="store_true",
        help="Apply noise reduction",
    )
    preprocess_parser.add_argument(
        "--normalize",
        action="store_true",
        default=True,
        help="Normalize audio levels (default: enabled)",
    )
    preprocess_parser.add_argument(
        "--trim-silence",
        action="store_true",
        help="Trim silence from beginning and end",
    )
    preprocess_parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Target sample rate in Hz (default: 16000)",
    )

    # Transcribe command
    transcribe_parser = subparsers.add_parser(
        "transcribe",
        help="Transcribe audio to text",
    )
    transcribe_parser.add_argument(
        "input",
        type=str,
        help="Input audio file",
    )
    transcribe_parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output directory (default: data/outputs/<slug>)",
    )
    transcribe_parser.add_argument(
        "-m", "--model",
        type=str,
        choices=["tiny", "tiny.en", "base", "base.en", "small", "small.en",
                 "medium", "medium.en", "large-v2", "large-v3"],
        help="Whisper model size (default: from config)",
    )
    transcribe_parser.add_argument(
        "-d", "--device",
        type=str,
        choices=["auto", "cuda", "cpu"],
        help="Device to use (default: auto)",
    )
    transcribe_parser.add_argument(
        "--diarize",
        action="store_true",
        help="Enable speaker diarization",
    )
    transcribe_parser.add_argument(
        "--diarization-mode",
        type=str,
        choices=["whisperx", "alt", "off"],
        help="Diarization mode (default: from config)",
    )
    transcribe_parser.add_argument(
        "--export",
        type=str,
        help="Export formats (comma-separated: txt,json,srt,vtt)",
    )

    # Diarize command
    diarize_parser = subparsers.add_parser(
        "diarize",
        help="Add speaker diarization to existing transcript",
    )
    diarize_parser.add_argument(
        "input",
        type=str,
        help="Input audio file or transcript JSON",
    )
    diarize_parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output directory",
    )
    diarize_parser.add_argument(
        "-m", "--mode",
        type=str,
        choices=["whisperx", "alt"],
        help="Diarization mode (default: whisperx)",
    )
    diarize_parser.add_argument(
        "--min-speakers",
        type=int,
        help="Minimum number of speakers",
    )
    diarize_parser.add_argument(
        "--max-speakers",
        type=int,
        help="Maximum number of speakers",
    )

    # Export command
    export_parser = subparsers.add_parser(
        "export",
        help="Export transcript to various formats",
    )
    export_parser.add_argument(
        "input",
        type=str,
        help="Input segments JSON file",
    )
    export_parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output directory",
    )
    export_parser.add_argument(
        "-f", "--formats",
        type=str,
        help="Export formats (comma-separated: txt,json,srt,vtt)",
    )
    export_parser.add_argument(
        "--word-level",
        action="store_true",
        help="Include word-level timestamps",
    )
    export_parser.add_argument(
        "--no-timestamps",
        action="store_true",
        help="Exclude timestamps from output",
    )

    # Batch command
    batch_parser = subparsers.add_parser(
        "batch",
        help="Batch process multiple audio files",
    )
    batch_parser.add_argument(
        "input_dir",
        type=str,
        help="Directory containing audio files",
    )
    batch_parser.add_argument(
        "-o", "--output-dir",
        type=str,
        help="Output directory (default: data/outputs)",
    )
    batch_parser.add_argument(
        "-m", "--model",
        type=str,
        help="Whisper model size",
    )
    batch_parser.add_argument(
        "--diarize",
        action="store_true",
        help="Enable speaker diarization",
    )
    batch_parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint",
    )
    batch_parser.add_argument(
        "--parallel",
        type=int,
        help="Number of parallel workers (default: 1)",
    )

    # Plan command
    plan_parser = subparsers.add_parser(
        "plan",
        help="Generate plan/outline from transcript",
    )
    plan_parser.add_argument(
        "input",
        type=str,
        help="Input segments JSON file",
    )
    plan_parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output file (default: <input>_plan.md)",
    )
    plan_parser.add_argument(
        "--format",
        type=str,
        choices=["markdown", "gdoc", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )

    # Sync command
    sync_parser = subparsers.add_parser(
        "sync",
        help="Sync outputs to cloud storage (rclone)",
    )
    sync_parser.add_argument(
        "--remote",
        type=str,
        help="rclone remote name (e.g., gdrive:TalkSmith)",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without syncing",
    )
    sync_parser.add_argument(
        "--direction",
        type=str,
        choices=["push", "pull", "sync"],
        default="push",
        help="Sync direction (default: push)",
    )

    return parser


def cmd_preprocess(args):
    """Handle preprocess command."""
    print(f"Preprocessing: {args.input}")
    print(f"  Denoise: {args.denoise}")
    print(f"  Normalize: {args.normalize}")
    print(f"  Trim silence: {args.trim_silence}")
    print(f"  Sample rate: {args.sample_rate}Hz")
    print(f"  Output: {args.output or 'data/outputs'}")

    # TODO: Implement actual preprocessing
    print("\n[!] Preprocessing implementation pending - see pipeline/preprocess.py")
    return 0


def cmd_transcribe(args):
    """Handle transcribe command."""
    print(f"Transcribing: {args.input}")
    print(f"  Model: {args.model or 'from config'}")
    print(f"  Device: {args.device or 'auto'}")
    print(f"  Diarize: {args.diarize}")

    if args.diarize:
        print(f"  Diarization mode: {args.diarization_mode or 'from config'}")

    if args.export:
        print(f"  Export formats: {args.export}")

    print(f"  Output: {args.output or 'data/outputs/<slug>'}")

    # TODO: Implement actual transcription
    print("\n[!] Transcription implementation pending - see pipeline/transcribe_fw.py")
    return 0


def cmd_diarize(args):
    """Handle diarize command."""
    print(f"Adding diarization: {args.input}")
    print(f"  Mode: {args.mode or 'whisperx'}")

    if args.min_speakers:
        print(f"  Min speakers: {args.min_speakers}")
    if args.max_speakers:
        print(f"  Max speakers: {args.max_speakers}")

    print(f"  Output: {args.output or 'same as input'}")

    # TODO: Implement actual diarization
    print("\n[!] Diarization implementation pending - see pipeline/diarize_whisperx.py")
    return 0


def cmd_export(args):
    """Handle export command."""
    print(f"Exporting: {args.input}")
    print(f"  Formats: {args.formats or 'from config'}")
    print(f"  Word-level: {args.word_level}")
    print(f"  Include timestamps: {not args.no_timestamps}")
    print(f"  Output: {args.output or 'same as input directory'}")

    # TODO: Implement actual export
    print("\n[!] Export implementation pending - see pipeline/export.py")
    return 0


def cmd_batch(args):
    """Handle batch command."""
    print(f"Batch processing: {args.input_dir}")
    print(f"  Model: {args.model or 'from config'}")
    print(f"  Diarize: {args.diarize}")
    print(f"  Resume: {args.resume}")
    print(f"  Parallel workers: {args.parallel or 1}")
    print(f"  Output: {args.output_dir or 'data/outputs'}")

    # TODO: Implement actual batch processing
    print("\n[!] Batch processing implementation pending - see scripts/batch_transcribe.py")
    return 0


def cmd_plan(args):
    """Handle plan command."""
    print(f"Generating plan: {args.input}")
    print(f"  Format: {args.format}")
    print(f"  Output: {args.output or f'{args.input}_plan.md'}")

    # TODO: Implement actual plan generation
    print("\n[!] Plan generation implementation pending - see pipeline/outline_from_segments.py")
    return 0


def cmd_sync(args):
    """Handle sync command."""
    print(f"Syncing to cloud storage")
    print(f"  Remote: {args.remote or 'from config'}")
    print(f"  Direction: {args.direction}")
    print(f"  Dry run: {args.dry_run}")

    # TODO: Implement actual sync
    print("\n[!] Cloud sync implementation pending - see scripts/sync_rclone.py")
    return 0


def main():
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Set up logging based on verbosity
    if args.verbose:
        print(f"TalkSmith CLI - Command: {args.command}")
        print(f"Config file: {args.config or 'default locations'}\n")

    # Dispatch to appropriate command handler
    handlers = {
        "preprocess": cmd_preprocess,
        "transcribe": cmd_transcribe,
        "diarize": cmd_diarize,
        "export": cmd_export,
        "batch": cmd_batch,
        "plan": cmd_plan,
        "sync": cmd_sync,
    }

    handler = handlers.get(args.command)
    if handler:
        try:
            return handler(args)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
