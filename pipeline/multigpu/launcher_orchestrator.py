"""
Orchestrator for multi-GPU launcher components.

Coordinates GPU detection, resource allocation, process spawning, and load balancing.
"""

from pathlib import Path
from typing import List, Optional

from pipeline.logger import get_logger

from .gpu_detector import GPUDetector
from .resource_allocator import ResourceAllocator
from .process_spawner import ProcessSpawner
from .load_balancer import LoadBalancer


class LauncherOrchestrator:
    """
    Orchestrates multi-GPU transcription workflow.

    This class coordinates all components:
    - GPUDetector: Identifies available GPUs
    - ResourceAllocator: Distributes workload
    - ProcessSpawner: Manages worker processes
    - LoadBalancer: Monitors progress and collects results

    This provides a high-level interface that maintains backward compatibility
    with the original run_multi_gpu function.
    """

    def __init__(self):
        """Initialize the orchestrator with all component instances."""
        self.gpu_detector = GPUDetector()
        self.resource_allocator = ResourceAllocator()
        self.process_spawner = ProcessSpawner()
        self.load_balancer = None  # Created when GPUs are known

        self.logger = get_logger(__name__, slug="multigpu-orchestrator")

    def run(
        self,
        input_dir: Path,
        output_dir: Path,
        gpus: List[int],
        model_size: str = "base",
        language: Optional[str] = None,
        pattern: str = "*.wav",
    ) -> int:
        """
        Run multi-GPU transcription workflow.

        This is the main entry point that coordinates all components.

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
        self.logger.log_start(
            "multi_gpu_transcription",
            input_dir=str(input_dir),
            gpus=gpus,
            model_size=model_size,
        )

        try:
            # Step 1: Validate GPUs
            is_valid, error_msg = self.gpu_detector.validate_gpus(gpus)
            if not is_valid:
                print(f"ERROR: {error_msg}")
                self.logger.error("GPU validation failed", error=error_msg)
                return 1

            # Step 2: Discover files
            files = self.resource_allocator.discover_files(input_dir, pattern)
            if not files:
                self.logger.warning(f"No files found matching {pattern}", pattern=pattern)
                print(f"No files found in {input_dir} matching {pattern}")
                return 0

            self.logger.info(f"Found {len(files)} files to process", file_count=len(files))

            # Print startup banner
            self._print_startup_banner(files, gpus, model_size, output_dir)

            # Step 3: Create queues and populate tasks
            task_queue = self.resource_allocator.create_task_queue(files, len(gpus))
            result_queue = self.resource_allocator.create_result_queue()

            # Step 4: Initialize load balancer
            self.load_balancer = LoadBalancer(gpus, logger=self.logger)

            # Step 5: Spawn worker processes
            processes = self.process_spawner.spawn_workers(
                gpu_ids=gpus,
                task_queue=task_queue,
                result_queue=result_queue,
                model_size=model_size,
                language=language,
                output_dir=output_dir,
            )

            # Step 6: Monitor progress
            self.load_balancer.monitor_progress(
                result_queue=result_queue,
                total_files=len(files),
                progress_callback=self.load_balancer.print_progress,
            )

            # Step 7: Wait for workers to finish
            self.process_spawner.wait_for_completion()

            # Step 8: Print summary and return exit code
            self.load_balancer.print_summary(len(files))

            stats = self.load_balancer.get_summary_stats()
            self.logger.log_complete(
                "multi_gpu_transcription",
                total_files=len(files),
                successful=stats["successful"],
                failed=stats["failed"],
                total_duration=stats["total_duration"],
                overall_rtf=stats["overall_rtf"],
                speedup=stats["speedup"],
            )

            return self.load_balancer.get_exit_code()

        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            self.logger.warning("Interrupted by user")
            self.process_spawner.terminate_all()
            return 130

        except Exception as e:
            self.logger.exception("Multi-GPU launcher failed", error=str(e))
            print(f"ERROR: {e}")
            self.process_spawner.terminate_all()
            return 1

    def _print_startup_banner(
        self, files: List[Path], gpus: List[int], model_size: str, output_dir: Path
    ) -> None:
        """
        Print startup information banner.

        Args:
            files: List of files to process
            gpus: List of GPU IDs
            model_size: Model size
            output_dir: Output directory
        """
        print("\n=== Multi-GPU Transcription ===")
        print(f"Files: {len(files)}")
        print(f"GPUs: {gpus}")
        print(f"Model: {model_size}")
        print(f"Output: {output_dir}\n")

    def validate_setup(
        self, input_dir: Path, gpus: List[int]
    ) -> tuple[bool, str]:
        """
        Validate the setup before running.

        Args:
            input_dir: Input directory path
            gpus: List of GPU IDs

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate input directory
        is_valid, error = self.resource_allocator.validate_input_dir(input_dir)
        if not is_valid:
            return False, error

        # Validate GPUs
        is_valid, error = self.gpu_detector.validate_gpus(gpus)
        if not is_valid:
            return False, error

        return True, ""

    def get_workload_info(self, input_dir: Path, pattern: str = "*.wav") -> dict:
        """
        Get information about the workload without running it.

        Args:
            input_dir: Input directory
            pattern: File pattern

        Returns:
            Dictionary with workload information
        """
        files = self.resource_allocator.discover_files(input_dir, pattern)
        return self.resource_allocator.estimate_workload(files)

    def get_gpu_info(self) -> dict:
        """
        Get information about available GPUs.

        Returns:
            Dictionary with GPU information
        """
        gpu_ids = self.gpu_detector.get_available_gpus()
        return {
            "count": len(gpu_ids),
            "ids": gpu_ids,
            "cuda_available": self.gpu_detector.is_cuda_available(),
            "details": [
                self.gpu_detector.get_gpu_info(gpu_id) for gpu_id in gpu_ids
            ],
        }

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.process_spawner:
            self.process_spawner.cleanup()
