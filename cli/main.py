#!/usr/bin/env python3
"""
TalkSmith CLI - Unified command-line interface for audio transcription.

Usage:
    python -m cli.main transcribe <input> [options]
    python -m cli.main batch <directory> [options]
    python -m cli.main export <segments> [options]
    python -m cli.main plan <segments> [options]
    python -m cli.main preprocess <input> [options]
    python -m cli.main sync <directory> [options]
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from config.settings import get_config


def setup_logging(verbose: bool = False):
    """
    Setup logging based on configuration and verbosity.

    Args:
        verbose: Enable verbose output
    """
    import logging

    config = get_config()
    level = config.get('Logging', 'level', fallback='INFO')

    if verbose:
        level = 'DEBUG'

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def cmd_transcribe(args):
    """Execute transcribe command."""
    print(f"[TRANSCRIBE] Processing: {args.input}")
    print(f"  Model: {args.model}")
    print(f"  Device: {args.device}")
    print(f"  Output: {args.output or 'auto-generated'}")
    print(f"  Diarization: {'enabled' if args.diarize else 'disabled'}")

    # TODO: Import and call actual transcription pipeline
    print("\n⚠️  Core transcription pipeline not yet implemented.")
    print("   This command will invoke: pipeline/transcribe_fw.py")
    return 1


def cmd_batch(args):
    """Execute batch processing command."""
    print(f"[BATCH] Processing directory: {args.input_dir}")
    print(f"  Model: {args.model}")
    print(f"  Pattern: {args.pattern}")
    print(f"  Resume: {'enabled' if args.resume else 'disabled'}")
    print(f"  Diarization: {'enabled' if args.diarize else 'disabled'}")

    # TODO: Implement batch processing
    print("\n⚠️  Batch processing not yet implemented.")
    print("   This command will invoke: scripts/batch_transcribe.py")
    return 1


def cmd_export(args):
    """Execute export command."""
    print(f"[EXPORT] Exporting: {args.segments}")
    print(f"  Formats: {', '.join(args.formats)}")
    print(f"  Output: {args.output or 'auto-generated'}")

    # TODO: Implement export functionality
    print("\n⚠️  Export functionality not yet implemented.")
    print("   This command will invoke: pipeline/export.py")
    return 1


def cmd_plan(args):
    """Execute plan generation command."""
    print(f"[PLAN] Generating plan from: {args.segments}")
    print(f"  Output: {args.output or 'auto-generated'}")
    print(f"  Format: {args.format}")

    # TODO: Implement plan generation
    print("\n⚠️  Plan generation not yet implemented.")
    print("   This command will invoke: pipeline/generate_plan.py")
    return 1


def cmd_preprocess(args):
    """Execute preprocessing command."""
    print(f"[PREPROCESS] Processing: {args.input}")
    print(f"  Denoise: {'enabled' if args.denoise else 'disabled'}")
    print(f"  Normalize: {'enabled' if args.normalize else 'disabled'}")
    print(f"  Trim silence: {'enabled' if args.trim_silence else 'disabled'}")
    print(f"  Output: {args.output or 'auto-generated'}")

    # TODO: Implement preprocessing
    print("\n⚠️  Preprocessing not yet implemented.")
    print("   This command will invoke: pipeline/preprocess.py")
    return 1


def cmd_sync(args):
    """Execute cloud sync command."""
    print(f"[SYNC] Syncing directory: {args.directory}")
    print(f"  Provider: {args.provider}")
    print(f"  Remote path: {args.remote_path or 'from config'}")

    # TODO: Implement cloud sync
    print("\n⚠️  Cloud sync not yet implemented.")
    print("   This command will use: rclone")
    return 1


def create_parser():
    """Create argument parser with all subcommands."""
    config = get_config()

    parser = argparse.ArgumentParser(
        description='TalkSmith - Local GPU-accelerated audio transcription',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Transcribe single file
  python -m cli.main transcribe audio.wav --model medium.en --diarize

  # Batch process directory
  python -m cli.main batch ./recordings --model large-v3 --resume

  # Export to multiple formats
  python -m cli.main export segments.json --formats txt,srt,vtt

  # Generate plan from transcript
  python -m cli.main plan segments.json --format markdown

For more information, see: https://github.com/DakotaIrsik/TalkSmith
        """
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file (default: config/settings.ini)'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Transcribe subcommand
    transcribe = subparsers.add_parser(
        'transcribe',
        help='Transcribe a single audio file'
    )
    transcribe.add_argument('input', help='Input audio file path')
    transcribe.add_argument(
        '--model',
        default=config.get('Models', 'whisper_model', fallback='large-v3'),
        help='Whisper model to use (default: from config)'
    )
    transcribe.add_argument(
        '--device',
        default=config.get('Models', 'whisper_device', fallback='auto'),
        help='Device to use: cuda, cpu, or auto (default: from config)'
    )
    transcribe.add_argument(
        '--diarize',
        action='store_true',
        help='Enable speaker diarization'
    )
    transcribe.add_argument(
        '--output', '-o',
        help='Output directory (default: data/outputs/<slug>)'
    )
    transcribe.add_argument(
        '--formats',
        nargs='+',
        default=config.get_list('Export', 'formats', fallback=['txt', 'json']),
        help='Export formats (default: from config)'
    )
    transcribe.set_defaults(func=cmd_transcribe)

    # Batch subcommand
    batch = subparsers.add_parser(
        'batch',
        help='Batch process a directory of audio files'
    )
    batch.add_argument('input_dir', help='Input directory containing audio files')
    batch.add_argument(
        '--model',
        default=config.get('Models', 'whisper_model', fallback='large-v3'),
        help='Whisper model to use (default: from config)'
    )
    batch.add_argument(
        '--pattern',
        default='*.{wav,mp3,m4a,flac}',
        help='File pattern to match (default: *.{wav,mp3,m4a,flac})'
    )
    batch.add_argument(
        '--diarize',
        action='store_true',
        help='Enable speaker diarization'
    )
    batch.add_argument(
        '--resume',
        action='store_true',
        help='Resume from previous run (skip completed files)'
    )
    batch.add_argument(
        '--parallel',
        type=int,
        help='Number of parallel workers (default: auto-detect GPUs)'
    )
    batch.set_defaults(func=cmd_batch)

    # Export subcommand
    export = subparsers.add_parser(
        'export',
        help='Export transcript to various formats'
    )
    export.add_argument('segments', help='Path to segments JSON file')
    export.add_argument(
        '--formats',
        nargs='+',
        default=['txt', 'json'],
        help='Export formats: txt, json, srt, vtt (default: txt json)'
    )
    export.add_argument(
        '--output', '-o',
        help='Output directory (default: same as segments file)'
    )
    export.set_defaults(func=cmd_export)

    # Plan subcommand
    plan = subparsers.add_parser(
        'plan',
        help='Generate plan/PRD from transcript'
    )
    plan.add_argument('segments', help='Path to segments JSON file')
    plan.add_argument(
        '--format',
        choices=['markdown', 'gdoc', 'txt'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    plan.add_argument(
        '--output', '-o',
        help='Output file path (default: auto-generated)'
    )
    plan.set_defaults(func=cmd_plan)

    # Preprocess subcommand
    preprocess = subparsers.add_parser(
        'preprocess',
        help='Preprocess audio file'
    )
    preprocess.add_argument('input', help='Input audio file path')
    preprocess.add_argument(
        '--denoise',
        action='store_true',
        help='Apply noise reduction'
    )
    preprocess.add_argument(
        '--normalize',
        action='store_true',
        help='Normalize audio levels'
    )
    preprocess.add_argument(
        '--trim-silence',
        action='store_true',
        help='Trim silence from beginning/end'
    )
    preprocess.add_argument(
        '--output', '-o',
        help='Output file path (default: <input>_preprocessed.wav)'
    )
    preprocess.set_defaults(func=cmd_preprocess)

    # Sync subcommand
    sync = subparsers.add_parser(
        'sync',
        help='Sync outputs to cloud storage'
    )
    sync.add_argument('directory', help='Directory to sync')
    sync.add_argument(
        '--provider',
        choices=['gdrive', 's3', 'dropbox'],
        default='gdrive',
        help='Cloud provider (default: gdrive)'
    )
    sync.add_argument(
        '--remote-path',
        help='Remote path (default: from config)'
    )
    sync.set_defaults(func=cmd_sync)

    return parser


def main():
    """Main entry point for CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Reload config if custom path provided
    if hasattr(args, 'config') and args.config:
        get_config(config_path=args.config, reload=True)

    # Execute command
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
