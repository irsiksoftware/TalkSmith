"""
Multi-GPU parallel transcription launcher.

Distributes batch transcription workloads across multiple GPUs using
multiprocessing with CUDA_VISIBLE_DEVICES isolation.

This launcher has been refactored into focused, single-responsibility classes:
- GPUDetector: GPU detection and validation
- ResourceAllocator: Workload distribution and queue management
- ProcessSpawner: Worker process lifecycle management
- LoadBalancer: Progress monitoring and metrics collection
- LauncherOrchestrator: High-level workflow coordination
"""

import argparse
import multiprocessing as mp
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.multigpu import (
    GPUDetector,
    LauncherOrchestrator,
)
from pipeline.logger import get_logger


def get_available_gpus() -> List[int]:
    """
    Detect available GPUs.

    This function maintains backward compatibility with the original API.

    Returns:
        List of GPU device IDs
    """
    detector = GPUDetector()
    return detector.get_available_gpus()


def run_multi_gpu(
    input_dir: Path,
    output_dir: Path,
    gpus: List[int],
    model_size: str = "base",
    language: Optional[str] = None,
    pattern: str = "*.wav",
) -> int:
    """
    Run multi-GPU transcription.

    This function now delegates to LauncherOrchestrator, which coordinates
    all the specialized components for a cleaner, more maintainable implementation.

    Args:
        input_dir: Input directory with audio files
        output_dir: Output directory
        gpus: List of GPU IDs to use
        model_size: Whisper model size
        language: Language code or None
        pattern: File glob pattern

    Returns:
        Exit code (0 for success, 1 for failures)
    """
    orchestrator = LauncherOrchestrator()
    return orchestrator.run(
        input_dir=input_dir,
        output_dir=output_dir,
        gpus=gpus,
        model_size=model_size,
        language=language,
        pattern=pattern,
    )


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-GPU parallel transcription launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use GPUs 0 and 1
  python launcher_multigpu.py --input-dir data/batch --gpus 0,1

  # Auto-detect all available GPUs
  python launcher_multigpu.py --input-dir data/batch --gpus auto

  # Specify model and language
  python launcher_multigpu.py --input-dir data/batch --gpus 0,1,2 \\
      --model-size large-v3 --language en
        """,
    )

    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Input directory containing audio files",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/outputs",
        help="Output directory (default: data/outputs)",
    )
    parser.add_argument(
        "--gpus",
        type=str,
        required=True,
        help="Comma-separated GPU IDs (e.g., '0,1,2') or 'auto' to detect all",
    )
    parser.add_argument(
        "--model-size",
        type=str,
        default="base",
        choices=["tiny", "base", "small", "medium", "medium.en", "large-v3"],
        help="Whisper model size (default: base)",
    )
    parser.add_argument(
        "--language",
        type=str,
        help="Language code (e.g., 'en'). Auto-detect if not specified.",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.wav",
        help="File pattern to match (default: *.wav)",
    )

    args = parser.parse_args()

    # Parse and validate GPU list using GPUDetector
    detector = GPUDetector()
    try:
        gpus = detector.parse_gpu_list(args.gpus)
        if args.gpus.lower() == "auto":
            print(f"Auto-detected {len(gpus)} GPU(s): {gpus}")
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1

    # Validate GPU availability
    is_valid, error_msg = detector.validate_gpus(gpus)
    if not is_valid:
        print(f"ERROR: {error_msg}")
        return 1

    # Resolve paths
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"ERROR: Input directory not found: {input_dir}")
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run multi-GPU transcription
    try:
        return run_multi_gpu(
            input_dir=input_dir,
            output_dir=output_dir,
            gpus=gpus,
            model_size=args.model_size,
            language=args.language,
            pattern=args.pattern,
        )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    # Set multiprocessing start method to 'spawn' for CUDA compatibility
    mp.set_start_method("spawn", force=True)
    sys.exit(main())
