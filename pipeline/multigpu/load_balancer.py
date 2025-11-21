"""
Load balancing and progress monitoring for multi-GPU workloads.

Monitors worker progress, collects results, and tracks performance metrics.
"""

import multiprocessing as mp
from pathlib import Path
from queue import Empty
from typing import List, Dict, Any, Optional, Callable

from pipeline.logger import BatchLogSummary, get_logger


class LoadBalancer:
    """
    Monitors and balances workload across GPUs.

    This class is responsible for:
    - Monitoring progress via result queue
    - Collecting and aggregating results
    - Tracking per-GPU statistics
    - Calculating performance metrics (RTF, speedup)
    """

    def __init__(self, gpu_ids: List[int], logger=None):
        """
        Initialize the load balancer.

        Args:
            gpu_ids: List of GPU IDs being used
            logger: Optional logger instance
        """
        self.gpu_ids = gpu_ids
        self.logger = logger or get_logger(__name__, slug="load-balancer")

        # Statistics tracking
        self.completed_count = 0
        self.total_duration = 0.0
        self.total_processing_time = 0.0
        self.gpu_stats = {
            gpu_id: {"processed": 0, "time": 0.0, "failures": 0}
            for gpu_id in gpu_ids
        }

        # Batch summary for success/failure tracking
        self.batch_summary = BatchLogSummary(self.logger)

        # Result storage
        self.results: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []

    def monitor_progress(
        self,
        result_queue: mp.Queue,
        total_files: int,
        progress_callback: Optional[Callable[[dict], None]] = None,
        timeout: float = 1.0,
    ) -> None:
        """
        Monitor progress by consuming results from the queue.

        Args:
            result_queue: Queue containing worker results
            total_files: Total number of files to process
            progress_callback: Optional callback for each result
            timeout: Queue get timeout in seconds
        """
        while self.completed_count < total_files:
            try:
                result = result_queue.get(timeout=timeout)
                self._process_result(result)

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(result)

            except Empty:
                continue

    def _process_result(self, result: dict) -> None:
        """
        Process a single result from a worker.

        Args:
            result: Result dictionary from worker
        """
        result_type = result.get("type")

        if result_type == "success":
            self._handle_success(result)
        elif result_type == "failure":
            self._handle_failure(result)
        elif result_type == "error":
            self._handle_error(result)

        self.results.append(result)

    def _handle_success(self, result: dict) -> None:
        """Handle a successful result."""
        self.completed_count += 1
        self.batch_summary.record_success(result["file"])

        # Update aggregate statistics
        self.total_duration += result["duration"]
        self.total_processing_time += result["processing_time"]

        # Update per-GPU statistics
        gpu_id = result["gpu_id"]
        self.gpu_stats[gpu_id]["processed"] += 1
        self.gpu_stats[gpu_id]["time"] += result["processing_time"]

    def _handle_failure(self, result: dict) -> None:
        """Handle a failed result."""
        self.completed_count += 1
        self.batch_summary.record_failure(result["file"], result["error"])

        # Track failure in GPU stats
        gpu_id = result["gpu_id"]
        self.gpu_stats[gpu_id]["failures"] += 1

        self.errors.append(result)

    def _handle_error(self, result: dict) -> None:
        """Handle a worker error."""
        gpu_id = result["gpu_id"]
        self.logger.error(
            f"Worker error on GPU {gpu_id}",
            gpu_id=gpu_id,
            error=result["error"]
        )
        self.errors.append(result)

    def get_overall_rtf(self) -> float:
        """
        Calculate overall Real-Time Factor.

        Returns:
            Overall RTF (processing_time / audio_duration)
        """
        if self.total_duration == 0:
            return 0.0
        return self.total_processing_time / self.total_duration

    def get_speedup(self) -> float:
        """
        Calculate speedup factor.

        Returns:
            Speedup (audio_duration / processing_time)
        """
        if self.total_processing_time == 0:
            return 0.0
        return self.total_duration / self.total_processing_time

    def get_per_gpu_stats(self) -> Dict[int, Dict[str, float]]:
        """
        Get statistics for each GPU.

        Returns:
            Dictionary mapping GPU ID to stats
        """
        return self.gpu_stats.copy()

    def get_summary_stats(self) -> dict:
        """
        Get comprehensive summary statistics.

        Returns:
            Dictionary with all performance metrics
        """
        return {
            "completed": self.completed_count,
            "successful": self.batch_summary.successful,
            "failed": self.batch_summary.failed,
            "total_duration": self.total_duration,
            "total_processing_time": self.total_processing_time,
            "overall_rtf": self.get_overall_rtf(),
            "speedup": self.get_speedup(),
            "gpu_stats": self.get_per_gpu_stats(),
            "error_count": len(self.errors),
        }

    def print_progress(self, result: dict) -> None:
        """
        Print progress update for a result.

        Args:
            result: Result dictionary
        """
        if result["type"] == "success":
            print(
                f"[{self.completed_count}/{self.get_expected_total()}] "
                f"GPU {result['gpu_id']}: {Path(result['file']).name} "
                f"(RTF: {result['rtf']:.3f})"
            )
        elif result["type"] == "failure":
            print(
                f"[{self.completed_count}/{self.get_expected_total()}] "
                f"GPU {result['gpu_id']}: FAILED {Path(result['file']).name} "
                f"- {result['error']}"
            )
        elif result["type"] == "error":
            print(f"ERROR on GPU {result['gpu_id']}: {result['error']}")

    def print_summary(self, total_files: int) -> None:
        """
        Print comprehensive summary of results.

        Args:
            total_files: Total number of files processed
        """
        stats = self.get_summary_stats()

        print("\n=== Summary ===")
        print(f"Total files: {total_files}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(
            f"Total audio duration: {stats['total_duration']:.2f}s "
            f"({stats['total_duration']/60:.2f}m)"
        )
        print(
            f"Total processing time: {stats['total_processing_time']:.2f}s "
            f"({stats['total_processing_time']/60:.2f}m)"
        )
        print(f"Overall RTF: {stats['overall_rtf']:.3f}")
        print(f"Speedup: {stats['speedup']:.2f}x")

        print("\n=== Per-GPU Stats ===")
        for gpu_id in sorted(stats['gpu_stats'].keys()):
            gpu_stat = stats['gpu_stats'][gpu_id]
            print(
                f"GPU {gpu_id}: {gpu_stat['processed']} files, "
                f"{gpu_stat['time']:.2f}s, {gpu_stat['failures']} failures"
            )

        if self.batch_summary.errors:
            print("\n=== Failed Files ===")
            for error in self.batch_summary.errors:
                print(f"  - {error['item']}: {error['error']}")

    def get_exit_code(self) -> int:
        """
        Get exit code based on batch summary.

        Returns:
            0 if all successful, 1 if any failures
        """
        return self.batch_summary.get_exit_code()

    def get_expected_total(self) -> int:
        """
        Get expected total files (for progress display).

        Returns:
            Expected total based on completed + pending
        """
        # This is set by monitor_progress
        return self.completed_count

    def reset(self) -> None:
        """Reset all statistics and counters."""
        self.completed_count = 0
        self.total_duration = 0.0
        self.total_processing_time = 0.0
        self.gpu_stats = {
            gpu_id: {"processed": 0, "time": 0.0, "failures": 0}
            for gpu_id in self.gpu_ids
        }
        self.results = []
        self.errors = []
        self.batch_summary = BatchLogSummary(self.logger)
