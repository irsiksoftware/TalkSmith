# Multi-GPU Launcher Components

This module provides focused, single-responsibility classes for managing multi-GPU transcription workloads.

## Overview

The multi-GPU launcher has been refactored from a monolithic "god function" (~500 lines) into 5 focused classes, each with a clear responsibility. This improves:

- **Maintainability**: Each class handles one concern
- **Testability**: Components can be tested in isolation
- **Extensibility**: Easy to add new features or swap implementations
- **Code Quality**: Follows SOLID principles

## Architecture

```
LauncherOrchestrator
├── GPUDetector         - GPU detection and validation
├── ResourceAllocator   - Workload distribution and queue management
├── ProcessSpawner      - Worker process lifecycle
└── LoadBalancer        - Progress monitoring and metrics
```

## Components

### 1. GPUDetector

**Responsibility**: Identify available GPUs and validate GPU configuration

**Key Methods**:
- `get_available_gpus()` - Detect available GPU devices
- `validate_gpus(gpu_ids)` - Validate requested GPUs are available
- `parse_gpu_list(spec)` - Parse GPU specification ('auto' or '0,1,2')
- `get_gpu_info(gpu_id)` - Get detailed GPU information

**Example**:
```python
from pipeline.multigpu import GPUDetector

detector = GPUDetector()
gpus = detector.get_available_gpus()
is_valid, error = detector.validate_gpus([0, 1])
```

### 2. ResourceAllocator

**Responsibility**: Discover files and distribute workload across GPUs

**Key Methods**:
- `discover_files(input_dir, pattern)` - Find files to process
- `distribute_workload(files, num_gpus)` - Distribute files across GPUs
- `create_task_queue(files, num_workers)` - Create populated task queue
- `estimate_workload(files)` - Get workload statistics

**Features**:
- Size-based sorting for better load balancing
- Round-robin distribution
- Workload estimation and statistics

**Example**:
```python
from pipeline.multigpu import ResourceAllocator

allocator = ResourceAllocator()
files = allocator.discover_files(Path("data/audio"), "*.wav")
task_queue = allocator.create_task_queue(files, num_workers=2)
```

### 3. ProcessSpawner

**Responsibility**: Create and manage worker processes

**Key Methods**:
- `spawn_workers(gpu_ids, task_queue, ...)` - Start worker processes
- `wait_for_completion(timeout)` - Wait for all workers to finish
- `terminate_all()` - Terminate all running workers
- `get_process_status()` - Get status of all processes

**Features**:
- One process per GPU with CUDA_VISIBLE_DEVICES isolation
- Graceful shutdown with sentinel values
- Process monitoring and cleanup

**Example**:
```python
from pipeline.multigpu import ProcessSpawner

spawner = ProcessSpawner()
processes = spawner.spawn_workers(
    gpu_ids=[0, 1],
    task_queue=task_queue,
    result_queue=result_queue,
    model_size="base",
    language=None,
    output_dir=Path("output")
)
spawner.wait_for_completion()
```

### 4. LoadBalancer

**Responsibility**: Monitor progress and collect performance metrics

**Key Methods**:
- `monitor_progress(result_queue, total_files)` - Monitor and collect results
- `get_overall_rtf()` - Calculate Real-Time Factor
- `get_speedup()` - Calculate speedup across GPUs
- `get_per_gpu_stats()` - Get per-GPU statistics
- `print_summary(total_files)` - Print comprehensive summary

**Metrics Tracked**:
- Per-GPU processing time and file count
- Overall RTF (Real-Time Factor)
- Speedup factor
- Success/failure counts
- Error tracking

**Example**:
```python
from pipeline.multigpu import LoadBalancer

balancer = LoadBalancer(gpu_ids=[0, 1])
balancer.monitor_progress(
    result_queue=result_queue,
    total_files=100,
    progress_callback=balancer.print_progress
)
balancer.print_summary(100)
```

### 5. LauncherOrchestrator

**Responsibility**: Coordinate all components and manage workflow

**Key Methods**:
- `run(input_dir, output_dir, gpus, ...)` - Main workflow execution
- `validate_setup(input_dir, gpus)` - Validate configuration
- `get_workload_info(input_dir, pattern)` - Get workload info
- `get_gpu_info()` - Get GPU information

**Workflow**:
1. Validate GPUs
2. Discover files
3. Create queues
4. Initialize load balancer
5. Spawn worker processes
6. Monitor progress
7. Wait for completion
8. Print summary and return exit code

**Example**:
```python
from pipeline.multigpu import LauncherOrchestrator

orchestrator = LauncherOrchestrator()
exit_code = orchestrator.run(
    input_dir=Path("data/audio"),
    output_dir=Path("data/outputs"),
    gpus=[0, 1],
    model_size="base",
    language="en",
    pattern="*.wav"
)
```

## Usage

### Basic Usage

The simplest way to use the refactored launcher is through the existing CLI:

```bash
# Auto-detect GPUs
python launcher_multigpu.py --input-dir data/audio --gpus auto

# Specify GPUs
python launcher_multigpu.py --input-dir data/audio --gpus 0,1,2 --model-size large-v3
```

### Programmatic Usage

You can also use the components programmatically:

```python
from pathlib import Path
from pipeline.multigpu import LauncherOrchestrator

# Create orchestrator
orchestrator = LauncherOrchestrator()

# Validate setup before running
is_valid, error = orchestrator.validate_setup(
    input_dir=Path("data/audio"),
    gpus=[0, 1]
)

if is_valid:
    # Run transcription
    exit_code = orchestrator.run(
        input_dir=Path("data/audio"),
        output_dir=Path("data/outputs"),
        gpus=[0, 1],
        model_size="base"
    )
```

### Custom Implementations

Each component can be used independently or customized:

```python
from pipeline.multigpu import GPUDetector, ResourceAllocator

# Use GPUDetector for GPU management
detector = GPUDetector()
gpus = detector.get_available_gpus()
for gpu_id in gpus:
    info = detector.get_gpu_info(gpu_id)
    print(f"GPU {gpu_id}: {info['name']}, {info['total_memory']} bytes")

# Use ResourceAllocator for workload analysis
allocator = ResourceAllocator()
files = allocator.discover_files(Path("data/audio"), "*.wav")
stats = allocator.estimate_workload(files)
print(f"Total files: {stats['file_count']}")
print(f"Total size: {stats['total_size']} bytes")
```

## Benefits

### Before Refactoring

- **launcher_multigpu.py**: 472 lines
- Single `run_multi_gpu()` function handling:
  - GPU detection
  - File discovery
  - Workload distribution
  - Queue management
  - Process spawning
  - Progress monitoring
  - Metrics calculation
  - Error handling
  - Summary printing

### After Refactoring

- **launcher_multigpu.py**: 188 lines (~60% reduction)
- **5 focused classes**: Each handling one responsibility
- **Better error handling**: Component-specific error handling
- **Improved logging**: Per-component logging with context
- **Easier testing**: Each component can be tested independently
- **Extensible**: Easy to add features or swap implementations

## Backward Compatibility

The refactoring maintains 100% backward compatibility:

1. The `run_multi_gpu()` function signature is unchanged
2. The CLI interface is identical
3. All behavior is preserved
4. No changes required to existing code using the launcher

## Testing

Each component can be tested in isolation:

```python
# Test GPUDetector
detector = GPUDetector()
assert detector.is_cuda_available() in [True, False]

# Test ResourceAllocator
allocator = ResourceAllocator()
files = [Path("a.wav"), Path("b.wav")]
distributed = allocator.distribute_workload(files, num_gpus=2)
assert len(distributed) == 2

# Test LoadBalancer
balancer = LoadBalancer(gpu_ids=[0])
assert balancer.get_overall_rtf() == 0.0  # Initially empty
```

## Future Enhancements

The modular design makes it easy to add new features:

1. **Advanced load balancing**: Implement dynamic load balancing based on GPU utilization
2. **Fault tolerance**: Add automatic retry and failover for worker failures
3. **Distributed execution**: Extend to support multi-node clusters
4. **Custom allocators**: Swap in different workload distribution strategies
5. **Monitoring dashboards**: Add real-time monitoring UI
6. **Checkpointing**: Add support for resuming interrupted jobs

## Migration Guide

For existing code using the old implementation:

**No changes required!** The refactoring is 100% backward compatible.

If you want to use the new components directly:

```python
# Old way
from launcher_multigpu import run_multi_gpu
exit_code = run_multi_gpu(input_dir, output_dir, gpus, model_size)

# New way (same result)
from pipeline.multigpu import LauncherOrchestrator
orchestrator = LauncherOrchestrator()
exit_code = orchestrator.run(input_dir, output_dir, gpus, model_size)

# Or use components individually
from pipeline.multigpu import GPUDetector, ResourceAllocator
detector = GPUDetector()
allocator = ResourceAllocator()
# ...
```
