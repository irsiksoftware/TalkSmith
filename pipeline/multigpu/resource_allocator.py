"""
Resource allocation for multi-GPU workloads.

Handles file discovery, workload distribution, and queue management.
"""

import multiprocessing as mp
from pathlib import Path
from typing import List, Tuple, Optional


class ResourceAllocator:
    """
    Allocates resources and distributes workload across GPUs.

    This class is responsible for:
    - Discovering input files
    - Distributing workload across GPUs
    - Creating and populating task queues
    """

    def __init__(self):
        """Initialize the resource allocator."""
        pass

    def discover_files(
        self, input_dir: Path, pattern: str = "*.wav"
    ) -> List[Path]:
        """
        Discover files matching the pattern in the input directory.

        Args:
            input_dir: Directory to search
            pattern: Glob pattern to match

        Returns:
            List of file paths
        """
        files = list(input_dir.glob(pattern))
        return files

    def distribute_workload(
        self, files: List[Path], num_gpus: int
    ) -> List[List[Path]]:
        """
        Distribute files across GPUs using round-robin with size-based sorting.

        For better load balancing, files are sorted by size (largest first)
        then distributed round-robin.

        Args:
            files: List of file paths
            num_gpus: Number of GPUs

        Returns:
            List of file lists, one per GPU
        """
        if not files:
            return [[] for _ in range(num_gpus)]

        # Sort by file size (largest first) for better load balancing
        files_with_size = [(f, self._get_file_size(f)) for f in files]
        files_with_size.sort(key=lambda x: x[1], reverse=True)
        sorted_files = [f for f, _ in files_with_size]

        # Distribute round-robin
        gpu_workloads = [[] for _ in range(num_gpus)]
        for i, file_path in enumerate(sorted_files):
            gpu_workloads[i % num_gpus].append(file_path)

        return gpu_workloads

    def create_task_queue(
        self, files: List[Path], num_workers: int
    ) -> mp.Queue:
        """
        Create and populate a task queue with files.

        Args:
            files: List of file paths to process
            num_workers: Number of worker processes (for sentinel values)

        Returns:
            Populated multiprocessing Queue
        """
        task_queue = mp.Queue()

        # Populate task queue with (file_path, index, total) tuples
        for i, file_path in enumerate(files):
            task_queue.put((str(file_path), i + 1, len(files)))

        # Add sentinel values for workers to know when to stop
        for _ in range(num_workers):
            task_queue.put(None)

        return task_queue

    def create_result_queue(self) -> mp.Queue:
        """
        Create a result queue for collecting worker results.

        Returns:
            Empty multiprocessing Queue
        """
        return mp.Queue()

    def estimate_workload(self, files: List[Path]) -> dict:
        """
        Estimate workload characteristics.

        Args:
            files: List of file paths

        Returns:
            Dictionary with workload statistics
        """
        if not files:
            return {
                "file_count": 0,
                "total_size": 0,
                "avg_size": 0,
                "min_size": 0,
                "max_size": 0,
            }

        sizes = [self._get_file_size(f) for f in files]

        return {
            "file_count": len(files),
            "total_size": sum(sizes),
            "avg_size": sum(sizes) / len(sizes),
            "min_size": min(sizes),
            "max_size": max(sizes),
        }

    @staticmethod
    def _get_file_size(file_path: Path) -> int:
        """
        Get file size in bytes.

        Args:
            file_path: Path to file

        Returns:
            File size in bytes
        """
        try:
            return file_path.stat().st_size
        except (OSError, FileNotFoundError):
            return 0

    def validate_input_dir(self, input_dir: Path) -> Tuple[bool, str]:
        """
        Validate input directory exists and is accessible.

        Args:
            input_dir: Path to input directory

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not input_dir.exists():
            return False, f"Input directory not found: {input_dir}"

        if not input_dir.is_dir():
            return False, f"Path is not a directory: {input_dir}"

        return True, ""

    def get_workload_distribution_stats(
        self, gpu_workloads: List[List[Path]]
    ) -> dict:
        """
        Get statistics about workload distribution across GPUs.

        Args:
            gpu_workloads: List of file lists per GPU

        Returns:
            Dictionary with distribution statistics
        """
        gpu_sizes = []
        gpu_counts = []

        for workload in gpu_workloads:
            total_size = sum(self._get_file_size(f) for f in workload)
            gpu_sizes.append(total_size)
            gpu_counts.append(len(workload))

        return {
            "gpu_count": len(gpu_workloads),
            "files_per_gpu": gpu_counts,
            "bytes_per_gpu": gpu_sizes,
            "avg_files_per_gpu": sum(gpu_counts) / len(gpu_counts) if gpu_counts else 0,
            "avg_bytes_per_gpu": sum(gpu_sizes) / len(gpu_sizes) if gpu_sizes else 0,
        }
