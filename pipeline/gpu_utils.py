"""
GPU utilities for device selection and memory monitoring.
"""

import logging
from typing import Dict, Optional


def get_gpu_info() -> Dict:
    """
    Get GPU information.

    Returns:
        Dictionary with GPU information including availability, count, and devices
    """
    try:
        import torch

        cuda_available = torch.cuda.is_available()
        device_count = torch.cuda.device_count() if cuda_available else 0

        devices = []
        if cuda_available and device_count > 0:
            for i in range(device_count):
                device_props = torch.cuda.get_device_properties(i)
                devices.append(
                    {
                        "id": i,
                        "name": device_props.name,
                        "total_memory_gb": round(device_props.total_memory / (1024**3), 2),
                        "total_memory_bytes": device_props.total_memory,
                        "compute_capability": f"{device_props.major}.{device_props.minor}",
                    }
                )

        return {
            "cuda_available": cuda_available,
            "device_count": device_count,
            "devices": devices,
        }
    except ImportError:
        return {
            "cuda_available": False,
            "device_count": 0,
            "devices": [],
        }
    except Exception:
        return {
            "cuda_available": False,
            "device_count": 0,
            "devices": [],
        }


def get_available_vram(device_id: int = 0) -> Optional[float]:
    """
    Get available VRAM on specified GPU in GB.

    Args:
        device_id: GPU device ID

    Returns:
        Available VRAM in GB, or None if not available
    """
    try:
        import torch

        if not torch.cuda.is_available():
            return None

        torch.cuda.set_device(device_id)
        torch.cuda.empty_cache()

        # Get memory info
        free_memory = torch.cuda.mem_get_info(device_id)[0]
        return round(free_memory / (1024**3), 2)
    except Exception:
        return None


def check_vram_sufficient(required_gb: float, device_id: int = 0) -> bool:
    """
    Check if GPU has sufficient VRAM for operation.

    Args:
        required_gb: Required VRAM in GB
        device_id: GPU device ID

    Returns:
        True if sufficient VRAM available, False otherwise
    """
    available = get_available_vram(device_id)
    if available is None:
        return False
    return available >= required_gb


def select_device(device: str = "auto", logger: Optional[logging.Logger] = None) -> str:
    """
    Select appropriate device based on availability and user preference.

    Args:
        device: Device preference ('auto', 'cuda', 'cpu')
        logger: Optional logger for logging device selection reasoning

    Returns:
        Selected device string ('cuda' or 'cpu')
    """
    if device not in ["auto", "cuda", "cpu"]:
        raise ValueError(f"Invalid device: {device}. Must be 'auto', 'cuda', or 'cpu'")

    # If user explicitly requests CPU or CUDA, respect that
    if device == "cpu":
        if logger:
            logger.info("Using CPU (user specified)")
        return "cpu"

    if device == "cuda":
        # User requested CUDA, verify it's available
        gpu_info = get_gpu_info()
        if not gpu_info["cuda_available"]:
            if logger:
                logger.warning(
                    "CUDA requested but not available. "
                    "Please check GPU setup with: python scripts/check_gpu.py"
                )
            raise RuntimeError("CUDA not available. Run 'python scripts/check_gpu.py' to diagnose.")
        if logger:
            logger.info(
                f"Using CUDA (user specified) - {gpu_info['device_count']} GPU(s) available"
            )
        return "cuda"

    # Auto mode: try CUDA first, fallback to CPU
    gpu_info = get_gpu_info()

    if gpu_info["cuda_available"] and gpu_info["device_count"] > 0:
        if logger:
            logger.info(f"Auto-selected CUDA - {gpu_info['device_count']} GPU(s) detected")
            for device_info in gpu_info["devices"]:
                logger.info(
                    f"  GPU {device_info['id']}: {device_info['name']} "
                    f"({device_info['total_memory_gb']} GB)"
                )
        return "cuda"
    else:
        if logger:
            logger.info(
                "Auto-selected CPU - No CUDA-capable GPU detected. "
                "For GPU support, run: python scripts/check_gpu.py"
            )
        return "cpu"


def suggest_model_for_vram(available_vram_gb: float) -> str:
    """
    Suggest appropriate Whisper model size based on available VRAM.

    Args:
        available_vram_gb: Available VRAM in GB

    Returns:
        Suggested model size
    """
    # Approximate VRAM requirements for faster-whisper models with float16
    # These are conservative estimates
    if available_vram_gb >= 10:
        return "large-v3"
    elif available_vram_gb >= 5:
        return "medium"
    elif available_vram_gb >= 2:
        return "small"
    elif available_vram_gb >= 1:
        return "base"
    else:
        return "tiny"


def get_memory_info(device_id: int = 0) -> Dict:
    """
    Get detailed memory information for specified GPU.

    Args:
        device_id: GPU device ID

    Returns:
        Dictionary with memory information
    """
    try:
        import torch

        if not torch.cuda.is_available():
            return {"error": "CUDA not available"}

        torch.cuda.set_device(device_id)
        torch.cuda.empty_cache()

        free_memory, total_memory = torch.cuda.mem_get_info(device_id)

        return {
            "device_id": device_id,
            "total_gb": round(total_memory / (1024**3), 2),
            "free_gb": round(free_memory / (1024**3), 2),
            "used_gb": round((total_memory - free_memory) / (1024**3), 2),
            "utilization_percent": round(((total_memory - free_memory) / total_memory) * 100, 1),
        }
    except Exception as e:
        return {"error": str(e)}
