"""
Multi-GPU parallel transcription launcher.

Distributes batch transcription workloads across multiple GPUs using
multiprocessing with CUDA_VISIBLE_DEVICES isolation.
"""

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path
from queue import Empty
from typing import List, Optional

try:
    import torch
except ImportError:
    torch = None

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

from pipeline.transcribe_fw import FasterWhisperTranscriber
from pipeline.logger import get_logger, BatchLogSummary


def get_available_gpus() -> List[int]:
    """
    Detect available GPUs.

    Returns:
        List of GPU device IDs
    """
    if torch is None or not torch.cuda.is_available():
        return []

    return list(range(torch.cuda.device_count()))


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes."""
    return file_path.stat().st_size


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

    Args:
        gpu_id: GPU device ID to use
        task_queue: Queue of (file_path, file_index) tuples
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


def distribute_workload(
    files: List[Path],
    num_gpus: int,
) -> List[List[Path]]:
    """
    Distribute files across GPUs using simple round-robin.

    For better load balancing, files are sorted by size (largest first)
    then distributed round-robin.

    Args:
        files: List of file paths
        num_gpus: Number of GPUs

    Returns:
        List of file lists, one per GPU
    """
    # Sort by file size (largest first) for better load balancing
    files_with_size = [(f, get_file_size(f)) for f in files]
    files_with_size.sort(key=lambda x: x[1], reverse=True)
    sorted_files = [f for f, _ in files_with_size]

    # Distribute round-robin
    gpu_workloads = [[] for _ in range(num_gpus)]
    for i, file_path in enumerate(sorted_files):
        gpu_workloads[i % num_gpus].append(file_path)

    return gpu_workloads


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

    Args:
        input_dir: Input directory with audio files
        output_dir: Output directory
        gpus: List of GPU IDs to use
        model_size: Whisper model size
        language: Language code or None
        pattern: File glob pattern

    Returns:
        Exit code (0 for success)
    """
    logger = get_logger(__name__, slug="multigpu-launcher")
    logger.log_start("multi_gpu_transcription", input_dir=str(input_dir), gpus=gpus)

    # Find files
    files = list(input_dir.glob(pattern))
    if not files:
        logger.warning(f"No files found matching {pattern}", pattern=pattern)
        print(f"No files found in {input_dir} matching {pattern}")
        return 0

    logger.info(f"Found {len(files)} files to process", file_count=len(files))
    print("\n=== Multi-GPU Transcription ===")
    print(f"Files: {len(files)}")
    print(f"GPUs: {gpus}")
    print(f"Model: {model_size}")
    print(f"Output: {output_dir}\n")

    # Create task queue and result queue
    task_queue = mp.Queue()
    result_queue = mp.Queue()

    # Populate task queue
    for i, file_path in enumerate(files):
        task_queue.put((str(file_path), i + 1, len(files)))

    # Add sentinel values for workers to know when to stop
    for _ in gpus:
        task_queue.put(None)

    # Start worker processes
    processes = []
    for gpu_id in gpus:
        p = mp.Process(
            target=worker_process,
            args=(gpu_id, task_queue, result_queue, model_size, language, output_dir),
        )
        p.start()
        processes.append(p)
        logger.info(f"Started worker on GPU {gpu_id}", gpu_id=gpu_id, pid=p.pid)

    # Monitor progress
    batch_summary = BatchLogSummary(logger)
    completed = 0
    total_duration = 0.0
    total_processing_time = 0.0
    gpu_stats = {gpu_id: {"processed": 0, "time": 0.0} for gpu_id in gpus}

    while completed < len(files):
        try:
            result = result_queue.get(timeout=1)

            if result["type"] == "success":
                completed += 1
                batch_summary.record_success(result["file"])
                total_duration += result["duration"]
                total_processing_time += result["processing_time"]
                gpu_stats[result["gpu_id"]]["processed"] += 1
                gpu_stats[result["gpu_id"]]["time"] += result["processing_time"]

                print(
                    f"[{completed}/{len(files)}] GPU {result['gpu_id']}: "
                    f"{Path(result['file']).name} "
                    f"(RTF: {result['rtf']:.3f})"
                )

            elif result["type"] == "failure":
                completed += 1
                batch_summary.record_failure(result["file"], result["error"])
                print(
                    f"[{completed}/{len(files)}] GPU {result['gpu_id']}: "
                    f"FAILED {Path(result['file']).name} - {result['error']}"
                )

            elif result["type"] == "error":
                logger.error(
                    f"Worker error on GPU {result['gpu_id']}", error=result["error"]
                )
                print(f"ERROR on GPU {result['gpu_id']}: {result['error']}")

        except Empty:
            continue

    # Wait for all workers to finish
    for p in processes:
        p.join()

    # Calculate final metrics
    overall_rtf = total_processing_time / total_duration if total_duration > 0 else 0
    speedup = total_duration / total_processing_time if total_processing_time > 0 else 0

    # Print summary
    print("\n=== Summary ===")
    print(f"Total files: {len(files)}")
    print(f"Successful: {batch_summary.successful}")
    print(f"Failed: {batch_summary.failed}")
    print(f"Total audio duration: {total_duration:.2f}s " f"({total_duration/60:.2f}m)")
    print(
        f"Total processing time: {total_processing_time:.2f}s "
        f"({total_processing_time/60:.2f}m)"
    )
    print(f"Overall RTF: {overall_rtf:.3f}")
    print(f"Speedup: {speedup:.2f}x")

    print("\n=== Per-GPU Stats ===")
    for gpu_id in sorted(gpu_stats.keys()):
        stats = gpu_stats[gpu_id]
        print(f"GPU {gpu_id}: {stats['processed']} files, {stats['time']:.2f}s")

    if batch_summary.errors:
        print("\n=== Failed Files ===")
        for error in batch_summary.errors:
            print(f"  - {error['item']}: {error['error']}")

    logger.log_complete(
        "multi_gpu_transcription",
        total_files=len(files),
        successful=batch_summary.successful,
        failed=batch_summary.failed,
        total_duration=total_duration,
        overall_rtf=overall_rtf,
        speedup=speedup,
    )

    return batch_summary.get_exit_code()


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

    # Parse GPU list
    if args.gpus.lower() == "auto":
        gpus = get_available_gpus()
        if not gpus:
            print("ERROR: No GPUs detected. Make sure CUDA is available.")
            return 1
        print(f"Auto-detected {len(gpus)} GPU(s): {gpus}")
    else:
        try:
            gpus = [int(g.strip()) for g in args.gpus.split(",")]
        except ValueError:
            print(f"ERROR: Invalid GPU list: {args.gpus}")
            print("Use comma-separated integers (e.g., '0,1,2') or 'auto'")
            return 1

    if not gpus:
        print("ERROR: No GPUs specified")
        return 1

    # Validate GPU availability
    available_gpus = get_available_gpus()
    if not available_gpus:
        print("ERROR: No GPUs detected. Make sure CUDA is available.")
        return 1

    for gpu_id in gpus:
        if gpu_id not in available_gpus:
            print(
                f"ERROR: GPU {gpu_id} not available. Available GPUs: {available_gpus}"
            )
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
