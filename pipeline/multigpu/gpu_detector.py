"""
GPU detection and capability identification.

Handles detection of available GPUs and validation of GPU availability.
"""

from typing import List, Dict, Any, Optional

try:
    import torch
except ImportError:
    torch = None


class GPUDetector:
    """
    Detects available GPUs and their capabilities.

    This class is responsible for:
    - Identifying available GPUs in the system
    - Validating GPU availability
    - Providing GPU capability information
    """

    def __init__(self):
        """Initialize the GPU detector."""
        self._cached_gpus: Optional[List[int]] = None

    def get_available_gpus(self) -> List[int]:
        """
        Detect available GPUs.

        Returns:
            List of GPU device IDs
        """
        if self._cached_gpus is not None:
            return self._cached_gpus

        if torch is None or not torch.cuda.is_available():
            self._cached_gpus = []
        else:
            self._cached_gpus = list(range(torch.cuda.device_count()))

        return self._cached_gpus

    def validate_gpus(self, requested_gpus: List[int]) -> tuple[bool, str]:
        """
        Validate that requested GPUs are available.

        Args:
            requested_gpus: List of GPU IDs to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not requested_gpus:
            return False, "No GPUs specified"

        available = self.get_available_gpus()

        if not available:
            return False, "No GPUs detected. Make sure CUDA is available."

        for gpu_id in requested_gpus:
            if gpu_id not in available:
                return False, f"GPU {gpu_id} not available. Available GPUs: {available}"

        return True, ""

    def get_gpu_count(self) -> int:
        """
        Get the number of available GPUs.

        Returns:
            Number of available GPUs
        """
        return len(self.get_available_gpus())

    def get_gpu_info(self, gpu_id: int) -> Dict[str, Any]:
        """
        Get information about a specific GPU.

        Args:
            gpu_id: GPU device ID

        Returns:
            Dictionary with GPU information (name, memory, etc.)
        """
        if torch is None or not torch.cuda.is_available():
            return {}

        if gpu_id >= torch.cuda.device_count():
            return {}

        props = torch.cuda.get_device_properties(gpu_id)

        return {
            "id": gpu_id,
            "name": props.name,
            "total_memory": props.total_memory,
            "major": props.major,
            "minor": props.minor,
            "multi_processor_count": props.multi_processor_count,
        }

    def is_cuda_available(self) -> bool:
        """
        Check if CUDA is available.

        Returns:
            True if CUDA is available, False otherwise
        """
        return torch is not None and torch.cuda.is_available()

    def parse_gpu_list(self, gpu_spec: str) -> List[int]:
        """
        Parse GPU specification string.

        Args:
            gpu_spec: GPU specification ('auto' or comma-separated list like '0,1,2')

        Returns:
            List of GPU IDs

        Raises:
            ValueError: If GPU specification is invalid
        """
        if gpu_spec.lower() == "auto":
            gpus = self.get_available_gpus()
            if not gpus:
                raise ValueError("No GPUs detected for auto-detection")
            return gpus

        try:
            gpus = [int(g.strip()) for g in gpu_spec.split(",")]
            return gpus
        except ValueError:
            raise ValueError(
                f"Invalid GPU list: {gpu_spec}. "
                "Use comma-separated integers (e.g., '0,1,2') or 'auto'"
            )
