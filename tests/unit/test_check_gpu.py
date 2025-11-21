"""Unit tests for GPU verification script."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from scripts.check_gpu import (
    check_cuda_availability,
    check_nvidia_driver,
    get_system_info,
    main,
    print_section,
    print_status,
)


class TestGetSystemInfo:
    """Test system information gathering."""

    def test_get_system_info_returns_dict(self):
        """Test that system info returns a dictionary with expected keys."""
        info = get_system_info()

        assert isinstance(info, dict)
        assert "platform" in info
        assert "python_version" in info
        assert "architecture" in info
        assert "processor" in info

    def test_get_system_info_has_valid_platform(self):
        """Test that platform is one of the expected values."""
        info = get_system_info()

        # Should be one of: Windows, Linux, Darwin (macOS), etc.
        assert info["platform"] in ["Windows", "Linux", "Darwin", "Java"]


class TestCheckCudaAvailability:
    """Test CUDA availability checking."""

    def test_cuda_available_with_devices(self):
        """Test CUDA detection when available with devices."""
        with patch.dict("sys.modules", {"torch": MagicMock()}):
            import sys

            mock_torch = sys.modules["torch"]

            mock_torch.__version__ = "2.0.0"
            mock_torch.cuda.is_available.return_value = True
            mock_torch.version.cuda = "11.8"
            mock_torch.cuda.device_count.return_value = 1

            # Mock device properties
            mock_props = MagicMock()
            mock_props.name = "NVIDIA GeForce RTX 3090"
            mock_props.total_memory = 24 * 1024**3  # 24 GB
            mock_props.major = 8
            mock_props.minor = 6
            mock_torch.cuda.get_device_properties.return_value = mock_props

            result = check_cuda_availability()

            assert result["cuda_available"] is True
            assert result["cuda_version"] == "11.8"
            assert result["device_count"] == 1
            assert len(result["devices"]) == 1
            assert result["devices"][0]["name"] == "NVIDIA GeForce RTX 3090"
            assert result["devices"][0]["total_memory_gb"] == 24.0

    def test_cuda_not_available(self):
        """Test CUDA detection when not available."""
        with patch.dict("sys.modules", {"torch": MagicMock()}):
            import sys

            mock_torch = sys.modules["torch"]

            mock_torch.__version__ = "2.0.0"
            mock_torch.cuda.is_available.return_value = False
            mock_torch.cuda.device_count.return_value = 0

            result = check_cuda_availability()

            assert result["cuda_available"] is False
            assert result["cuda_version"] is None
            assert result["device_count"] == 0
            assert result["devices"] == []

    def test_cuda_check_without_torch_installed(self):
        """Test CUDA check when PyTorch is not installed."""
        with patch.dict("sys.modules", {"torch": None}):
            # Force import error
            with patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'torch'"),
            ):
                result = check_cuda_availability()

                assert result["cuda_available"] is False
                assert "error" in result
                assert "PyTorch not installed" in result["error"]

    def test_cuda_check_with_multiple_gpus(self):
        """Test CUDA detection with multiple GPUs."""
        with patch.dict("sys.modules", {"torch": MagicMock()}):
            import sys

            mock_torch = sys.modules["torch"]

            mock_torch.__version__ = "2.0.0"
            mock_torch.cuda.is_available.return_value = True
            mock_torch.version.cuda = "11.8"
            mock_torch.cuda.device_count.return_value = 2

            # Mock device properties for two GPUs
            mock_props_1 = MagicMock()
            mock_props_1.name = "NVIDIA A100"
            mock_props_1.total_memory = 40 * 1024**3
            mock_props_1.major = 8
            mock_props_1.minor = 0

            mock_props_2 = MagicMock()
            mock_props_2.name = "NVIDIA A100"
            mock_props_2.total_memory = 40 * 1024**3
            mock_props_2.major = 8
            mock_props_2.minor = 0

            mock_torch.cuda.get_device_properties.side_effect = [
                mock_props_1,
                mock_props_2,
            ]

            result = check_cuda_availability()

            assert result["device_count"] == 2
            assert len(result["devices"]) == 2


class TestCheckNvidiaDriver:
    """Test NVIDIA driver checking."""

    def test_nvidia_driver_available(self):
        """Test when nvidia-smi is available."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "535.104.05\n"

        with patch("subprocess.run", return_value=mock_result):
            version = check_nvidia_driver()

            assert version == "535.104.05"

    def test_nvidia_driver_not_available(self):
        """Test when nvidia-smi is not available."""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            version = check_nvidia_driver()

            assert version is None

    def test_nvidia_driver_timeout(self):
        """Test timeout handling for nvidia-smi."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("nvidia-smi", 5)):
            version = check_nvidia_driver()

            assert version is None

    def test_nvidia_driver_multiple_versions(self):
        """Test when multiple GPU driver versions are returned."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "535.104.05\n535.104.05\n"

        with patch("subprocess.run", return_value=mock_result):
            version = check_nvidia_driver()

            # Should return first version
            assert version == "535.104.05"


class TestPrintFunctions:
    """Test print utility functions."""

    def test_print_section(self, capsys):
        """Test section header printing."""
        print_section("Test Section")
        captured = capsys.readouterr()

        assert "Test Section" in captured.out
        assert "=" in captured.out

    def test_print_section_custom_char(self, capsys):
        """Test section header with custom character."""
        print_section("Test", "-")
        captured = capsys.readouterr()

        assert "Test" in captured.out
        assert "-" in captured.out

    def test_print_status_success(self, capsys):
        """Test status printing for success."""
        print_status("Label", "Value", True)
        captured = capsys.readouterr()

        assert "Label" in captured.out
        assert "Value" in captured.out
        assert "✓" in captured.out

    def test_print_status_failure(self, capsys):
        """Test status printing for failure."""
        print_status("Label", "Value", False)
        captured = capsys.readouterr()

        assert "Label" in captured.out
        assert "Value" in captured.out
        assert "✗" in captured.out


class TestMain:
    """Test main function execution."""

    @patch("scripts.check_gpu.check_nvidia_driver")
    @patch("scripts.check_gpu.check_cuda_availability")
    @patch("scripts.check_gpu.get_system_info")
    def test_main_all_checks_pass(self, mock_sys_info, mock_cuda, mock_driver):
        """Test main function when all checks pass."""
        # Mock system info
        mock_sys_info.return_value = {
            "platform": "Linux",
            "platform_release": "5.15.0",
            "architecture": "x86_64",
            "python_version": "3.10.0",
        }

        # Mock driver check
        mock_driver.return_value = "535.104.05"

        # Mock CUDA check
        mock_props = MagicMock()
        mock_props.name = "NVIDIA RTX 3090"
        mock_props.total_memory = 24 * 1024**3
        mock_props.major = 8
        mock_props.minor = 6

        mock_cuda.return_value = {
            "torch_version": "2.0.0",
            "cuda_available": True,
            "cuda_version": "11.8",
            "cudnn_available": True,
            "cudnn_version": 8902,
            "device_count": 1,
            "devices": [
                {
                    "id": 0,
                    "name": "NVIDIA RTX 3090",
                    "total_memory_gb": 24.0,
                    "compute_capability": "8.6",
                }
            ],
        }

        # Mock the GPU test
        with patch.dict("sys.modules", {"torch": MagicMock()}):
            import sys

            mock_torch = sys.modules["torch"]
            mock_tensor = MagicMock()
            mock_torch.randn.return_value.cuda.return_value = mock_tensor
            mock_torch.matmul.return_value = mock_tensor

            exit_code = main()

            assert exit_code == 0

    @patch("scripts.check_gpu.check_nvidia_driver")
    @patch("scripts.check_gpu.check_cuda_availability")
    @patch("scripts.check_gpu.get_system_info")
    def test_main_no_cuda_available(self, mock_sys_info, mock_cuda, mock_driver):
        """Test main function when CUDA is not available."""
        mock_sys_info.return_value = {
            "platform": "Linux",
            "platform_release": "5.15.0",
            "architecture": "x86_64",
            "python_version": "3.10.0",
        }

        mock_driver.return_value = None

        mock_cuda.return_value = {
            "torch_version": "2.0.0",
            "cuda_available": False,
            "cuda_version": None,
            "device_count": 0,
            "devices": [],
        }

        exit_code = main()

        assert exit_code == 1

    @patch("scripts.check_gpu.check_nvidia_driver")
    @patch("scripts.check_gpu.check_cuda_availability")
    @patch("scripts.check_gpu.get_system_info")
    def test_main_pytorch_not_installed(self, mock_sys_info, mock_cuda, mock_driver):
        """Test main function when PyTorch is not installed."""
        mock_sys_info.return_value = {
            "platform": "Linux",
            "platform_release": "5.15.0",
            "architecture": "x86_64",
            "python_version": "3.10.0",
        }

        mock_driver.return_value = "535.104.05"

        mock_cuda.return_value = {
            "torch_version": None,
            "cuda_available": False,
            "cuda_version": None,
            "device_count": 0,
            "devices": [],
            "error": "PyTorch not installed",
        }

        exit_code = main()

        assert exit_code == 1

    @patch("scripts.check_gpu.check_nvidia_driver")
    @patch("scripts.check_gpu.check_cuda_availability")
    @patch("scripts.check_gpu.get_system_info")
    def test_main_multi_gpu_setup(self, mock_sys_info, mock_cuda, mock_driver):
        """Test main function with multi-GPU setup."""
        mock_sys_info.return_value = {
            "platform": "Linux",
            "platform_release": "5.15.0",
            "architecture": "x86_64",
            "python_version": "3.10.0",
        }

        mock_driver.return_value = "535.104.05"

        mock_cuda.return_value = {
            "torch_version": "2.0.0",
            "cuda_available": True,
            "cuda_version": "11.8",
            "cudnn_available": True,
            "cudnn_version": 8902,
            "device_count": 4,
            "devices": [
                {
                    "id": i,
                    "name": f"GPU{i}",
                    "total_memory_gb": 40.0,
                    "compute_capability": "8.0",
                }
                for i in range(4)
            ],
        }

        with patch.dict("sys.modules", {"torch": MagicMock()}):
            import sys

            mock_torch = sys.modules["torch"]
            mock_tensor = MagicMock()
            mock_torch.randn.return_value.cuda.return_value = mock_tensor
            mock_torch.matmul.return_value = mock_tensor

            exit_code = main()

            assert exit_code == 0

    @patch("scripts.check_gpu.check_nvidia_driver")
    @patch("scripts.check_gpu.check_cuda_availability")
    @patch("scripts.check_gpu.get_system_info")
    def test_main_gpu_test_failure(self, mock_sys_info, mock_cuda, mock_driver):
        """Test main function when GPU test fails."""
        mock_sys_info.return_value = {
            "platform": "Linux",
            "platform_release": "5.15.0",
            "architecture": "x86_64",
            "python_version": "3.10.0",
        }

        mock_driver.return_value = "535.104.05"

        mock_cuda.return_value = {
            "torch_version": "2.0.0",
            "cuda_available": True,
            "cuda_version": "11.8",
            "cudnn_available": True,
            "cudnn_version": 8902,
            "device_count": 1,
            "devices": [
                {
                    "id": 0,
                    "name": "NVIDIA RTX 3090",
                    "total_memory_gb": 24.0,
                    "compute_capability": "8.6",
                }
            ],
        }

        # Mock GPU test failure
        with patch.dict("sys.modules", {"torch": MagicMock()}):
            import sys

            mock_torch = sys.modules["torch"]
            mock_torch.randn.return_value.cuda.side_effect = RuntimeError("CUDA out of memory")

            exit_code = main()

            assert exit_code == 1
