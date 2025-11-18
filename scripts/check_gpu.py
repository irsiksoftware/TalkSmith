#!/usr/bin/env python3
"""
GPU Verification Script for TalkSmith
Detects GPUs and logs driver/CUDA versions.
Confirms GPU visibility to PyTorch.
"""

import platform
import sys
from typing import Dict, List, Optional


def get_system_info() -> Dict[str, str]:
    """Get basic system information."""
    return {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
    }


def check_cuda_availability() -> Dict[str, any]:
    """Check CUDA availability through PyTorch."""
    try:
        import torch

        cuda_available = torch.cuda.is_available()
        cuda_version = torch.version.cuda if cuda_available else None
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
                        "compute_capability": f"{device_props.major}.{device_props.minor}",
                    }
                )

        return {
            "torch_version": torch.__version__,
            "cuda_available": cuda_available,
            "cuda_version": cuda_version,
            "cudnn_available": (torch.backends.cudnn.is_available() if cuda_available else False),
            "cudnn_version": (
                torch.backends.cudnn.version()
                if cuda_available and torch.backends.cudnn.is_available()
                else None
            ),
            "device_count": device_count,
            "devices": devices,
        }
    except ImportError:
        return {
            "torch_version": None,
            "cuda_available": False,
            "cuda_version": None,
            "cudnn_available": False,
            "cudnn_version": None,
            "device_count": 0,
            "devices": [],
            "error": "PyTorch not installed",
        }
    except Exception as e:
        return {
            "torch_version": None,
            "cuda_available": False,
            "cuda_version": None,
            "cudnn_available": False,
            "cudnn_version": None,
            "device_count": 0,
            "devices": [],
            "error": str(e),
        }


def check_nvidia_driver() -> Optional[str]:
    """Check NVIDIA driver version using nvidia-smi."""
    import subprocess

    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def print_section(title: str, char: str = "="):
    """Print a section header."""
    print(f"\n{char * 70}")
    print(f"  {title}")
    print(f"{char * 70}\n")


def print_status(label: str, value: any, success: bool = True):
    """Print a status line with color coding."""
    status_symbol = "✓" if success else "✗"
    print(f"  {status_symbol} {label:30s}: {value}")


def main():
    """Main execution function."""
    print("\n" + "=" * 70)
    print("  TalkSmith GPU Verification")
    print("=" * 70)

    # System Information
    print_section("System Information", "-")
    sys_info = get_system_info()
    print_status("Operating System", f"{sys_info['platform']} {sys_info['platform_release']}")
    print_status("Architecture", sys_info["architecture"])
    print_status("Python Version", sys_info["python_version"])

    # NVIDIA Driver
    print_section("NVIDIA Driver", "-")
    driver_version = check_nvidia_driver()
    if driver_version:
        print_status("Driver Version", driver_version, True)
        print_status("nvidia-smi", "Available", True)
    else:
        print_status("Driver", "NOT DETECTED", False)
        print("  ⚠ nvidia-smi not found or failed to execute")
        print("  ⚠ Please ensure NVIDIA drivers are installed")

    # CUDA and PyTorch
    print_section("CUDA and PyTorch", "-")
    cuda_info = check_cuda_availability()

    if "error" in cuda_info:
        print_status("PyTorch", f"ERROR: {cuda_info['error']}", False)
        print("\n  ⚠ PyTorch is not installed or could not be imported")
        print("  ⚠ Please install PyTorch with CUDA support:")
        print(
            "     pip install torch torchvision torchaudio "
            "--index-url https://download.pytorch.org/whl/cu118"
        )
        return 1

    print_status("PyTorch Version", cuda_info["torch_version"])
    print_status("CUDA Available", cuda_info["cuda_available"], cuda_info["cuda_available"])

    if cuda_info["cuda_available"]:
        print_status("CUDA Version", cuda_info["cuda_version"])
        print_status("GPU Device Count", cuda_info["device_count"])
        print_status(
            "CuDNN Available",
            cuda_info["cudnn_available"],
            cuda_info["cudnn_available"],
        )
        if cuda_info["cudnn_available"]:
            print_status("CuDNN Version", cuda_info["cudnn_version"])
    else:
        print("  ⚠ CUDA is not available to PyTorch")
        if driver_version:
            print("  ⚠ NVIDIA driver detected but CUDA not available to PyTorch")
            print("  ⚠ This may indicate a version mismatch or incorrect PyTorch installation")
        return 1

    # GPU Devices
    if cuda_info["devices"]:
        print_section("Detected GPU Devices", "-")
        for device in cuda_info["devices"]:
            print(f"\n  GPU {device['id']}:")
            print(f"    Name              : {device['name']}")
            print(f"    Total Memory      : {device['total_memory_gb']} GB")
            print(f"    Compute Capability: {device['compute_capability']}")

        # Test GPU
        print_section("GPU Functionality Test", "-")
        try:
            import torch

            test_tensor = torch.randn(1000, 1000).cuda()
            result = torch.matmul(test_tensor, test_tensor)
            print_status("Basic CUDA Operations", "PASSED", True)
            print(f"    Test: 1000x1000 matrix multiplication on GPU 0")
            del test_tensor, result
            torch.cuda.empty_cache()
        except Exception as e:
            print_status("Basic CUDA Operations", f"FAILED: {e}", False)
            return 1

    # Summary
    print_section("Summary", "=")
    if cuda_info["cuda_available"] and cuda_info["device_count"] > 0:
        print("  ✓ All checks passed!")
        print(f"  ✓ {cuda_info['device_count']} GPU(s) detected and operational")
        print("  ✓ TalkSmith is ready for GPU-accelerated transcription")

        if cuda_info["device_count"] >= 2:
            print(f"\n  🚀 Multi-GPU setup detected ({cuda_info['device_count']} GPUs)")
            print("     You can use multi-GPU parallelism features!")

        return 0
    else:
        print("  ✗ GPU verification failed")
        print("  ✗ Please review the errors above and consult docs/prereqs.md")
        return 1


if __name__ == "__main__":
    sys.exit(main())
