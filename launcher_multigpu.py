"""
Multi-GPU parallel transcription launcher - Refactored.

Distributes batch transcription workloads across multiple GPUs using
multiprocessing with CUDA_VISIBLE_DEVICES isolation.

Refactored into focused classes following Single Responsibility Principle:
- GPUDetector: GPU detection and validation
- WorkloadBalancer: File distribution logic
- MultiGPUOrchestrator: Main coordination
- ProgressTracker: Progress monitoring and statistics
- GPUWorkload: Data class for workload
"""

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty
from typing import List, Optional, Dict

try:
    import torch
except ImportError:
    torch = None

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.transcribe_fw import FasterWhisperTranscriber
from pipeline.logger import get_logger, BatchLogSummary


@dataclass
class GPUWorkload:
    """Represents workload for a single GPU."""

    gpu_id: int
    files: List[Path] = field(default_factory=list)
    total_size: int = 0

    def add_file(self, file_path: Path):
        """Add file to this GPU's workload."""
        self.files.append(file_path)
        self.total_size += file_path.stat().st_size


class GPUDetector:
    """Detects and validates available GPUs."""

    def __init__(self, logger=None):
        self.logger = logger or get_logger(__name__)

    def get_available_gpus(self) -> List[int]:
        """
        Detect available CUDA GPUs.

        Returns:
            List of GPU device IDs
        """
        if torch is None or not torch.cuda.is_available():
            self.logger.warning("CUDA not available")
            return []

        gpu_count = torch.cuda.device_count()
        self.logger.info(f"Detected {gpu_count} GPU(s)", gpu_count=gpu_count)
        return list(range(gpu_count))

    def validate_gpu_ids(
        self, requested_ids: List[int], available: Optional[List[int]] = None
    ) -> List[int]:
        """
        Validate requested GPU IDs against available.

        Args:
            requested_ids: User-requested GPU IDs
            available: Available GPU IDs (auto-detect if None)

        Returns:
            Valid GPU IDs

        Raises:
            ValueError: If no valid GPUs
        """
        if available is None:
            available = self.get_available_gpus()

        valid = [gpu_id for gpu_id in requested_ids if gpu_id in available]

        if not valid:
            raise ValueError(
                f"No valid GPUs. Requested: {requested_ids}, Available: {available}"
            )

        if len(valid) < len(requested_ids):
            invalid = set(requested_ids) - set(valid)
            self.logger.warning(f"Invalid GPU IDs ignored: {invalid}")

        return valid


class WorkloadBalancer:
    """Balances file workload across GPUs."""

    def __init__(self, logger=None):
        self.logger = logger or get_logger(__name__)

    def balance_by_size(self, files: List[Path], num_gpus: int) -> List[GPUWorkload]:
        """
        Distribute files across GPUs by size for balanced load.

        Uses greedy algorithm: sort files by size (largest first),
        then assign each to GPU with smallest current workload.

        Args:
            files: List of audio files
            num_gpus: Number of GPUs

        Returns:
            List of GPUWorkload objects
        """
        # Sort files by size (largest first)
        sorted_files = sorted(files, key=lambda f: f.stat().st_size, reverse=True)

        # Create workloads for each GPU
        workloads = [GPUWorkload(gpu_id=i) for i in range(num_gpus)]

        # Greedy assignment: assign each file to GPU with smallest current workload
        for file_path in sorted_files:
            # Find GPU with smallest workload
            min_workload = min(workloads, key=lambda w: w.total_size)
            min_workload.add_file(file_path)

        # Log distribution
        for workload in workloads:
            self.logger.info(
                f"GPU {workload.gpu_id}: {len(workload.files)} files, "
                f"{workload.total_size / 1024**2:.1f} MB",
                gpu_id=workload.gpu_id,
                file_count=len(workload.files),
                size_mb=workload.total_size / 1024**2,
            )

        return workloads


class ProgressTracker:
    """Tracks and displays progress for multi-GPU transcription."""

    def __init__(self, total_files: int, num_gpus: int, logger=None):
        self.total_files = total_files
        self.num_gpus = num_gpus
        self.logger = logger or get_logger(__name__)

        # Overall statistics
        self.completed = 0
        self.batch_summary = BatchLogSummary(self.logger)

        # Performance metrics
        self.total_duration = 0.0
        self.total_processing_time = 0.0

        # Per-GPU statistics
        self.gpu_stats = {}
        for i in range(num_gpus):
            self.gpu_stats[i] = {"processed": 0, "time": 0.0}

    def monitor_queue(self, result_queue: mp.Queue) -> Dict:
        """
        Monitor result queue and track progress.

        Args:
            result_queue: Queue with worker results

        Returns:
            Summary dictionary
        """
        while self.completed < self.total_files:
            try:
                result = result_queue.get(timeout=1)
                self._process_result(result)

            except Empty:
                continue

        return self.get_summary()

    def _process_result(self, result: Dict):
        """Process a single result from a worker."""
        result_type = result["type"]

        if result_type == "success":
            self.completed += 1
            self.batch_summary.record_success(result["file"])
            self.total_duration += result["duration"]
            self.total_processing_time += result["processing_time"]
            self.gpu_stats[result["gpu_id"]]["processed"] += 1
            self.gpu_stats[result["gpu_id"]]["time"] += result["processing_time"]

            self._print_success(result)

        elif result_type == "failure":
            self.completed += 1
            self.batch_summary.record_failure(result["file"], result["error"])
            self._print_failure(result)

        elif result_type == "error":
            self.logger.error(
                f"Worker error on GPU {result['gpu_id']}", error=result["error"]
            )
            print(f"ERROR on GPU {result['gpu_id']}: {result['error']}")

    def _print_success(self, result: Dict):
        """Print success message."""
        print(
            f"[{self.completed}/{self.total_files}] GPU {result['gpu_id']}: "
            f"{Path(result['file']).name} "
            f"(RTF: {result['rtf']:.3f})"
        )

    def _print_failure(self, result: Dict):
        """Print failure message."""
        print(
            f"[{self.completed}/{self.total_files}] GPU {result['gpu_id']}: "
            f"FAILED {Path(result['file']).name} - {result['error']}"
        )

    def get_summary(self) -> Dict:
        """
        Get final summary statistics.

        Returns:
            Dictionary with summary statistics
        """
        overall_rtf = (
            self.total_processing_time / self.total_duration
            if self.total_duration > 0
            else 0
        )
        speedup = (
            self.total_duration / self.total_processing_time
            if self.total_processing_time > 0
            else 0
        )

        return {
            "total_files": self.total_files,
            "successful": self.batch_summary.successful,
            "failed": self.batch_summary.failed,
            "total_duration": self.total_duration,
            "total_processing_time": self.total_processing_time,
            "overall_rtf": overall_rtf,
            "speedup": speedup,
            "gpu_stats": self.gpu_stats,
            "errors": self.batch_summary.errors,
        }

    def print_summary(self):
        """Print final summary to console."""
        summary = self.get_summary()

        print("\n=== Summary ===")
        print(f"Total files: {summary['total_files']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(
            f"Total audio duration: {summary['total_duration']:.2f}s "
            f"({summary['total_duration']/60:.2f}m)"
        )
        print(
            f"Total processing time: {summary['total_processing_time']:.2f}s "
            f"({summary['total_processing_time']/60:.2f}m)"
        )
        print(f"Overall RTF: {summary['overall_rtf']:.3f}")
        print(f"Speedup: {summary['speedup']:.2f}x")

        print("\n=== Per-GPU Stats ===")
        for gpu_id in sorted(summary["gpu_stats"].keys()):
            stats = summary["gpu_stats"][gpu_id]
            print(f"GPU {gpu_id}: {stats['processed']} files, {stats['time']:.2f}s")

        if summary["errors"]:
            print("\n=== Failed Files ===")
            for error in summary["errors"]:
                print(f"  - {error['item']}: {error['error']}")


class MultiGPUOrchestrator:
    """Orchestrates multi-GPU transcription."""

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        gpu_ids: List[int],
        model_size: str = "base",
        language: Optional[str] = None,
        pattern: str = "*.wav",
        logger=None,
    ):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.gpu_ids = gpu_ids
        self.model_size = model_size
        self.language = language
        self.pattern = pattern
        self.logger = logger or get_logger(__name__, slug="multigpu-launcher")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> int:
        """
        Run multi-GPU transcription.

        Returns:
            Exit code (0 for success)
        """
        self.logger.log_start(
            "multi_gpu_transcription", input_dir=str(self.input_dir), gpus=self.gpu_ids
        )

        # Scan audio files
        files = self._scan_audio_files()
        if not files:
            self.logger.warning(
                f"No files found matching {self.pattern}", pattern=self.pattern
            )
            print(f"No files found in {self.input_dir} matching {self.pattern}")
            return 0

        self.logger.info(f"Found {len(files)} files to process", file_count=len(files))
        self._print_header(len(files))

        # Create queues
        task_queue = mp.Queue()
        result_queue = mp.Queue()

        # Populate task queue
        self._populate_task_queue(task_queue, files)

        # Start worker processes
        processes = self._start_workers(task_queue, result_queue)

        # Monitor progress
        tracker = ProgressTracker(
            total_files=len(files), num_gpus=len(self.gpu_ids), logger=self.logger
        )
        summary = tracker.monitor_queue(result_queue)

        # Wait for workers to finish
        for p in processes:
            p.join()

        # Print summary
        tracker.print_summary()

        # Log completion
        self.logger.log_complete(
            "multi_gpu_transcription",
            total_files=summary["total_files"],
            successful=summary["successful"],
            failed=summary["failed"],
            total_duration=summary["total_duration"],
            overall_rtf=summary["overall_rtf"],
            speedup=summary["speedup"],
        )

        return 0 if summary["failed"] == 0 else 1

    def _scan_audio_files(self) -> List[Path]:
        """Scan input directory for audio files."""
        return list(self.input_dir.glob(self.pattern))

    def _print_header(self, file_count: int):
        """Print header information."""
        print("\n=== Multi-GPU Transcription ===")
        print(f"Files: {file_count}")
        print(f"GPUs: {self.gpu_ids}")
        print(f"Model: {self.model_size}")
        print(f"Output: {self.output_dir}\n")

    def _populate_task_queue(self, task_queue: mp.Queue, files: List[Path]):
        """Populate task queue with file tasks."""
        for i, file_path in enumerate(files):
            task_queue.put((str(file_path), i + 1, len(files)))

        # Add sentinel values for workers to know when to stop
        for _ in self.gpu_ids:
            task_queue.put(None)

    def _start_workers(
        self, task_queue: mp.Queue, result_queue: mp.Queue
    ) -> List[mp.Process]:
        """Start worker processes on each GPU."""
        processes = []
        for gpu_id in self.gpu_ids:
            p = mp.Process(
                target=self._worker_process,
                args=(gpu_id, task_queue, result_queue),
            )
            p.start()
            processes.append(p)
            self.logger.info(f"Started worker on GPU {gpu_id}", gpu_id=gpu_id, pid=p.pid)

        return processes

    def _worker_process(
        self, gpu_id: int, task_queue: mp.Queue, result_queue: mp.Queue
    ):
        """
        Worker process that processes files on a specific GPU.

        Args:
            gpu_id: GPU device ID to use
            task_queue: Queue of (file_path, file_index, total_files) tuples
            result_queue: Queue for results
        """
        # Set CUDA_VISIBLE_DEVICES to isolate this process to one GPU
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)

        # Create logger for this worker
        logger = get_logger(__name__, slug=f"gpu-{gpu_id}")
        logger.info(
            f"Worker started on GPU {gpu_id}", gpu_id=gpu_id, model_size=self.model_size
        )

        # Initialize transcriber (will use device 0 since CUDA_VISIBLE_DEVICES is set)
        try:
            transcriber = FasterWhisperTranscriber(
                model_size=self.model_size,
                device="cuda",
                compute_type="float16",
                logger=logger,
            )
        except Exception as e:
            logger.error(f"Failed to initialize transcriber on GPU {gpu_id}", error=str(e))
            result_queue.put({"type": "error", "gpu_id": gpu_id, "error": str(e)})
            return

        processed = 0

        # Process tasks from queue
        while True:
            try:
                task = task_queue.get(timeout=1)
                if task is None:  # Sentinel value to stop worker
                    break

                file_path, file_index, total_files = task
                file_path = Path(file_path)

                logger.info(
                    f"Processing {file_path.name}",
                    file=str(file_path),
                    index=file_index,
                    total=total_files,
                )

                try:
                    # Transcribe
                    start_time = time.time()
                    result = transcriber.transcribe(str(file_path), language=self.language)
                    elapsed = time.time() - start_time

                    # Save outputs
                    output_subdir = self.output_dir / file_path.stem
                    output_subdir.mkdir(parents=True, exist_ok=True)

                    # Save JSON
                    json_path = output_subdir / f"{file_path.stem}.json"
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)

                    # Save text
                    txt_path = output_subdir / f"{file_path.stem}.txt"
                    with open(txt_path, "w", encoding="utf-8") as f:
                        f.write(result["text"])

                    logger.info(
                        f"Completed {file_path.name}",
                        file=str(file_path),
                        duration=result["duration"],
                        processing_time=elapsed,
                        rtf=result["rtf"],
                    )

                    processed += 1

                    # Send result back
                    result_queue.put(
                        {
                            "type": "success",
                            "gpu_id": gpu_id,
                            "file": str(file_path),
                            "duration": result["duration"],
                            "processing_time": elapsed,
                            "rtf": result["rtf"],
                            "output_dir": str(output_subdir),
                        }
                    )

                except Exception as e:
                    logger.exception(f"Failed to process {file_path.name}", error=str(e))
                    result_queue.put(
                        {
                            "type": "failure",
                            "gpu_id": gpu_id,
                            "file": str(file_path),
                            "error": str(e),
                        }
                    )

            except Empty:
                continue
            except Exception as e:
                logger.exception("Worker error", error=str(e))
                result_queue.put(
                    {
                        "type": "error",
                        "gpu_id": gpu_id,
                        "error": str(e),
                    }
                )
                break

        logger.info(f"Worker finished on GPU {gpu_id}", gpu_id=gpu_id, processed=processed)


def main():
    """CLI entry point - Refactored to be < 50 lines."""
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
        "--input-dir", type=str, required=True, help="Input directory containing audio files"
    )
    parser.add_argument(
        "--output-dir", type=str, default="data/outputs", help="Output directory (default: data/outputs)"
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
        "--language", type=str, help="Language code (e.g., 'en'). Auto-detect if not specified."
    )
    parser.add_argument(
        "--pattern", type=str, default="*.wav", help="File pattern to match (default: *.wav)"
    )

    args = parser.parse_args()

    # Detect and validate GPUs
    detector = GPUDetector()

    if args.gpus.lower() == "auto":
        gpu_ids = detector.get_available_gpus()
        if not gpu_ids:
            print("ERROR: No GPUs detected. Make sure CUDA is available.")
            return 1
        print(f"Auto-detected {len(gpu_ids)} GPU(s): {gpu_ids}")
    else:
        try:
            requested_gpus = [int(g.strip()) for g in args.gpus.split(",")]
            gpu_ids = detector.validate_gpu_ids(requested_gpus)
        except ValueError as e:
            print(f"ERROR: {e}")
            return 1
        except Exception:
            print(f"ERROR: Invalid GPU list: {args.gpus}")
            print("Use comma-separated integers (e.g., '0,1,2') or 'auto'")
            return 1

    # Validate paths
    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"ERROR: Input directory not found: {input_dir}")
        return 1

    output_dir = Path(args.output_dir)

    # Run orchestrator
    try:
        orchestrator = MultiGPUOrchestrator(
            input_dir=input_dir,
            output_dir=output_dir,
            gpu_ids=gpu_ids,
            model_size=args.model_size,
            language=args.language,
            pattern=args.pattern,
        )
        return orchestrator.run()
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
