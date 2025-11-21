"""
Process spawning and management for multi-GPU workers.

Handles creation and lifecycle management of worker processes.
"""

import multiprocessing as mp
import os
import sys
import time
import json
from pathlib import Path
from queue import Empty
from typing import List, Optional, Callable

# Add parent directories for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pipeline.logger import get_logger
from pipeline.transcribe_fw import FasterWhisperTranscriber


def worker_process(
    gpu_id: int,
    task_queue: mp.Queue,
    result_queue: mp.Queue,
    model_size: str,
    language: Optional[str],
    output_dir: Path,
):
    """
    Worker process that processes files on a specific GPU.

    This function runs in a separate process and processes tasks from the queue.

    Args:
        gpu_id: GPU device ID to use
        task_queue: Queue of (file_path, file_index, total_files) tuples
        result_queue: Queue for results
        model_size: Whisper model size
        language: Language code or None
        output_dir: Output directory for results
    """
    # Set CUDA_VISIBLE_DEVICES to isolate this process to one GPU
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)

    # Create logger for this worker
    logger = get_logger(__name__, slug=f"gpu-{gpu_id}")
    logger.info(f"Worker started on GPU {gpu_id}", gpu_id=gpu_id, model_size=model_size)

    # Initialize transcriber (will use device 0 since CUDA_VISIBLE_DEVICES is set)
    try:
        transcriber = FasterWhisperTranscriber(
            model_size=model_size,
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
                result = transcriber.transcribe(str(file_path), language=language)
                elapsed = time.time() - start_time

                # Save outputs
                output_subdir = output_dir / file_path.stem
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


class ProcessSpawner:
    """
    Spawns and manages worker processes for multi-GPU execution.

    This class is responsible for:
    - Creating worker processes
    - Managing process lifecycle
    - Tracking process status
    """

    def __init__(self):
        """Initialize the process spawner."""
        self.processes: List[mp.Process] = []
        self.logger = get_logger(__name__, slug="process-spawner")

    def spawn_workers(
        self,
        gpu_ids: List[int],
        task_queue: mp.Queue,
        result_queue: mp.Queue,
        model_size: str,
        language: Optional[str],
        output_dir: Path,
        worker_func: Callable = worker_process,
    ) -> List[mp.Process]:
        """
        Spawn worker processes, one per GPU.

        Args:
            gpu_ids: List of GPU IDs to use
            task_queue: Queue containing tasks
            result_queue: Queue for collecting results
            model_size: Whisper model size
            language: Language code or None
            output_dir: Output directory for results
            worker_func: Worker function to run (default: worker_process)

        Returns:
            List of started Process objects
        """
        processes = []

        for gpu_id in gpu_ids:
            p = mp.Process(
                target=worker_func,
                args=(gpu_id, task_queue, result_queue, model_size, language, output_dir),
            )
            p.start()
            processes.append(p)
            self.logger.info(f"Started worker on GPU {gpu_id}", gpu_id=gpu_id, pid=p.pid)

        self.processes = processes
        return processes

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all worker processes to complete.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            True if all processes completed, False if timeout occurred
        """
        for p in self.processes:
            p.join(timeout=timeout)
            if p.is_alive():
                return False

        return True

    def terminate_all(self):
        """Terminate all running worker processes."""
        for p in self.processes:
            if p.is_alive():
                self.logger.warning(f"Terminating process {p.pid}", pid=p.pid)
                p.terminate()

        # Give processes time to terminate gracefully
        time.sleep(0.5)

        # Force kill if still alive
        for p in self.processes:
            if p.is_alive():
                self.logger.warning(f"Force killing process {p.pid}", pid=p.pid)
                p.kill()

    def get_process_count(self) -> int:
        """
        Get the number of spawned processes.

        Returns:
            Number of processes
        """
        return len(self.processes)

    def get_alive_count(self) -> int:
        """
        Get the number of processes still running.

        Returns:
            Number of alive processes
        """
        return sum(1 for p in self.processes if p.is_alive())

    def get_process_status(self) -> List[dict]:
        """
        Get status information for all processes.

        Returns:
            List of dictionaries with process status
        """
        status = []
        for i, p in enumerate(self.processes):
            status.append(
                {
                    "index": i,
                    "pid": p.pid,
                    "alive": p.is_alive(),
                    "exitcode": p.exitcode,
                }
            )
        return status

    def cleanup(self):
        """Clean up process resources."""
        for p in self.processes:
            if p.is_alive():
                p.terminate()
            p.join(timeout=1)
            if p.is_alive():
                p.kill()

        self.processes = []
