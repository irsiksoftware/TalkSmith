#!/usr/bin/env python3
"""
Batch transcription script for TalkSmith.

Processes all audio files in an input directory with resume capability,
progress tracking, parallel processing support, and multi-format export.
"""

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Set

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.exporters import export_all
from pipeline.logger import BatchLogSummary, get_logger
from pipeline.transcribe_fw import FasterWhisperTranscriber


class ProgressState:
    """Track batch transcription progress."""

    def __init__(self, cache_file: Path):
        """
        Initialize progress state.

        Args:
            cache_file: Path to progress cache file
        """
        self.cache_file = cache_file
        self.completed_files: Set[str] = set()
        self.failed_files: Dict[str, str] = {}
        self.load()

    def load(self):
        """Load progress state from cache file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.completed_files = set(data.get("completed", []))
                    self.failed_files = data.get("failed", {})
            except Exception:
                # If cache is corrupted, start fresh
                self.completed_files = set()
                self.failed_files = {}

    def save(self):
        """Save progress state to cache file."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(
                {"completed": list(self.completed_files), "failed": self.failed_files},
                f,
                indent=2,
            )

    def mark_completed(self, filename: str):
        """Mark a file as completed."""
        self.completed_files.add(filename)
        # Remove from failed if it was there
        self.failed_files.pop(filename, None)
        self.save()

    def mark_failed(self, filename: str, error: str):
        """Mark a file as failed."""
        self.failed_files[filename] = error
        self.save()

    def is_completed(self, filename: str) -> bool:
        """Check if a file has been completed."""
        return filename in self.completed_files

    def should_retry(self, filename: str, retry_failed: bool) -> bool:
        """Check if a failed file should be retried."""
        if filename not in self.failed_files:
            return True
        return retry_failed


class BatchTranscriber:
    """Batch transcription with resume capability and progress tracking."""

    SUPPORTED_FORMATS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus"}

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        model_size: str = "base",
        device: str = "cuda",
        language: Optional[str] = None,
        formats: Optional[List[str]] = None,
        resume: bool = True,
        retry_failed: bool = False,
        max_retries: int = 3,
        parallel: bool = False,
        workers: int = 1,
    ):
        """
        Initialize batch transcriber.

        Args:
            input_dir: Directory containing audio files
            output_dir: Directory for output files
            model_size: Whisper model size
            device: Device to use (cuda or cpu)
            language: Language code (e.g., 'en') or None for auto-detect
            formats: List of export formats (default: ['txt', 'srt', 'vtt', 'json'])
            resume: Enable resume from last processed file
            retry_failed: Retry previously failed files
            max_retries: Maximum retry attempts for failed files
            parallel: Enable parallel processing
            workers: Number of parallel workers (for multi-file processing)
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.model_size = model_size
        self.device = device
        self.language = language
        self.formats = formats or ["txt", "srt", "vtt", "json"]
        self.resume = resume
        self.retry_failed = retry_failed
        self.max_retries = max_retries
        self.parallel = parallel
        self.workers = workers

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize logger
        slug = f"batch-{self.input_dir.name}"
        self.logger = get_logger(__name__, slug=slug)
        self.batch_summary = BatchLogSummary(self.logger)

        # Progress tracking
        cache_dir = Path(".cache")
        self.progress = ProgressState(cache_dir / "batch_progress.json")

    def _get_audio_files(self) -> List[Path]:
        """Get all audio files from input directory."""
        audio_files = []
        for ext in self.SUPPORTED_FORMATS:
            audio_files.extend(self.input_dir.glob(f"*{ext}"))
        return sorted(audio_files)

    def _transcribe_file(
        self, audio_file: Path, retry_count: int = 0
    ) -> Dict[str, any]:
        """
        Transcribe a single file with retry logic.

        Args:
            audio_file: Path to audio file
            retry_count: Current retry attempt number

        Returns:
            Dictionary with transcription results and metadata
        """
        result = {
            "filename": audio_file.name,
            "status": "processing",
            "error": None,
        }

        try:
            self.logger.log_start("transcription", audio_file=audio_file.name)

            # Initialize transcriber (each worker needs its own instance)
            transcriber = FasterWhisperTranscriber(
                model_size=self.model_size, device=self.device, logger=self.logger
            )

            # Transcribe
            transcription = transcriber.transcribe(
                str(audio_file), language=self.language
            )

            # Export to multiple formats
            output_files = export_all(
                segments=transcription["segments"],
                output_dir=self.output_dir,
                base_name=audio_file.stem,
                formats=self.formats,
                logger=self.logger,
            )

            # Update result
            result.update(
                {
                    "status": "completed",
                    "duration": transcription["duration"],
                    "processing_time": transcription["processing_time"],
                    "rtf": transcription["rtf"],
                    "language": transcription["language"],
                    "language_probability": transcription["language_probability"],
                    "output_files": {
                        fmt: str(path) for fmt, path in output_files.items()
                    },
                }
            )

            self.logger.log_complete(
                "transcription",
                duration=transcription["processing_time"],
                audio_file=audio_file.name,
                rtf=transcription["rtf"],
                language=transcription["language"],
            )

            self.batch_summary.record_success(audio_file.name)
            self.progress.mark_completed(audio_file.name)

        except Exception as e:
            error_msg = str(e)
            result.update({"status": "failed", "error": error_msg})

            # Retry logic
            if retry_count < self.max_retries:
                self.logger.warning(
                    f"Retry {retry_count + 1}/{self.max_retries} for {audio_file.name}",
                    audio_file=audio_file.name,
                    retry=retry_count + 1,
                    error=error_msg,
                )
                time.sleep(2**retry_count)  # Exponential backoff
                return self._transcribe_file(audio_file, retry_count + 1)

            self.logger.error(
                f"Failed to transcribe {audio_file.name}",
                audio_file=audio_file.name,
                error=error_msg,
            )
            self.batch_summary.record_failure(audio_file.name, error_msg)
            self.progress.mark_failed(audio_file.name, error_msg)

        return result

    def _transcribe_file_worker(self, audio_file_path: str) -> Dict[str, any]:
        """Worker function for parallel processing."""
        return self._transcribe_file(Path(audio_file_path))

    def _calculate_eta(
        self, processed: int, total: int, elapsed_time: float
    ) -> str:
        """Calculate estimated time remaining."""
        if processed == 0:
            return "unknown"

        avg_time_per_file = elapsed_time / processed
        remaining = total - processed
        eta_seconds = avg_time_per_file * remaining

        hours = int(eta_seconds // 3600)
        minutes = int((eta_seconds % 3600) // 60)
        seconds = int(eta_seconds % 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def run(self) -> int:
        """
        Run batch transcription.

        Returns:
            Exit code (0 for success, 1 if any failures)
        """
        audio_files = self._get_audio_files()

        if not audio_files:
            self.logger.warning(f"No audio files found in {self.input_dir}")
            print(f"No audio files found in {self.input_dir}")
            return 0

        # Filter files based on resume/retry settings
        files_to_process = []
        for audio_file in audio_files:
            if self.resume and self.progress.is_completed(audio_file.name):
                continue
            if not self.progress.should_retry(audio_file.name, self.retry_failed):
                continue
            files_to_process.append(audio_file)

        total_files = len(audio_files)
        already_completed = len(audio_files) - len(files_to_process)

        self.logger.info(
            "Starting batch transcription",
            total_files=total_files,
            to_process=len(files_to_process),
            already_completed=already_completed,
            model_size=self.model_size,
            device=self.device,
            language=self.language or "auto-detect",
            formats=self.formats,
            parallel=self.parallel,
            workers=self.workers if self.parallel else 1,
        )

        print(f"Found {total_files} audio file(s)")
        print(f"Already completed: {already_completed}")
        print(f"To process: {len(files_to_process)}")
        print(f"Model: {self.model_size}")
        print(f"Device: {self.device}")
        print(f"Language: {self.language or 'auto-detect'}")
        print(f"Output formats: {', '.join(self.formats)}")
        print(f"Output directory: {self.output_dir}")
        print(f"Parallel: {self.parallel} (workers: {self.workers if self.parallel else 1})")
        print(f"Resume: {self.resume}")
        print(f"Retry failed: {self.retry_failed}")
        print()

        if not files_to_process:
            print("All files already processed!")
            return 0

        start_time = time.time()
        processed = 0

        if self.parallel and self.workers > 1:
            # Parallel processing (multi-file)
            print(f"Processing {len(files_to_process)} files in parallel...")
            print()

            with ProcessPoolExecutor(max_workers=self.workers) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(
                        self._transcribe_file_worker, str(audio_file)
                    ): audio_file
                    for audio_file in files_to_process
                }

                # Process results as they complete
                for future in as_completed(future_to_file):
                    audio_file = future_to_file[future]
                    processed += 1
                    elapsed = time.time() - start_time
                    eta = self._calculate_eta(processed, len(files_to_process), elapsed)

                    try:
                        result = future.result()
                        if result["status"] == "completed":
                            print(
                                f"[{processed}/{len(files_to_process)}] ✓ {audio_file.name} "
                                f"(RTF: {result['rtf']:.3f}, ETA: {eta})"
                            )
                        else:
                            print(
                                f"[{processed}/{len(files_to_process)}] ✗ {audio_file.name} "
                                f"- {result['error']}"
                            )
                    except Exception as e:
                        print(
                            f"[{processed}/{len(files_to_process)}] ✗ {audio_file.name} "
                            f"- {str(e)}"
                        )
        else:
            # Sequential processing
            for i, audio_file in enumerate(files_to_process, 1):
                elapsed = time.time() - start_time
                eta = self._calculate_eta(i - 1, len(files_to_process), elapsed)

                print(f"[{i}/{len(files_to_process)}] {audio_file.name} (ETA: {eta})")

                result = self._transcribe_file(audio_file)

                if result["status"] == "completed":
                    print(
                        f"  ✓ Completed in {result['processing_time']:.2f}s "
                        f"(RTF: {result['rtf']:.3f})"
                    )
                else:
                    print(f"  ✗ Failed: {result['error']}")

                print()
                processed += 1

        # Summary
        elapsed_total = time.time() - start_time
        self.batch_summary.print_summary()

        print("=" * 60)
        print("Batch transcription complete")
        print(f"Total files: {total_files}")
        print(f"Already completed: {already_completed}")
        print(f"Newly processed: {processed}")
        print(f"Successful: {self.batch_summary.successful}")
        print(f"Failed: {self.batch_summary.failed}")
        print(f"Total time: {elapsed_total:.2f}s")
        print(f"Progress file: {self.progress.cache_file}")
        print("=" * 60)

        return self.batch_summary.get_exit_code()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Batch transcribe audio files with resume capability"
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        default="data/inputs",
        help="Input directory with audio files (default: data/inputs)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/outputs",
        help="Output directory (default: data/outputs)",
    )
    parser.add_argument(
        "--model",
        "--model-size",
        dest="model_size",
        default="base",
        choices=["tiny", "base", "small", "medium", "medium.en", "large-v3"],
        help="Whisper model size (default: base)",
    )
    parser.add_argument(
        "--device",
        default="cuda",
        choices=["cuda", "cpu"],
        help="Device to use (default: cuda)",
    )
    parser.add_argument(
        "--language",
        help="Language code (e.g., 'en'). Auto-detect if not specified.",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        default=["txt", "srt", "vtt", "json"],
        choices=["txt", "srt", "vtt", "json"],
        help="Output formats (default: txt srt vtt json)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Resume from last processed file (default: True)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_false",
        dest="resume",
        help="Disable resume capability",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry previously failed files",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts per file (default: 3)",
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel processing (multi-file)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Number of parallel workers (default: 2)",
    )

    args = parser.parse_args()

    try:
        batch_transcriber = BatchTranscriber(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            model_size=args.model_size,
            device=args.device,
            language=args.language,
            formats=args.formats,
            resume=args.resume,
            retry_failed=args.retry_failed,
            max_retries=args.max_retries,
            parallel=args.parallel,
            workers=args.workers,
        )

        exit_code = batch_transcriber.run()
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n\nBatch transcription interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger = get_logger(__name__)
        logger.exception("Fatal error in batch transcription")
        print(f"\n\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
