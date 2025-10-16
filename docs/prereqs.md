# TalkSmith Prerequisites

This document covers the installation and verification of prerequisites for running TalkSmith.

## Table of Contents
- [System Requirements](#system-requirements)
- [Windows Setup](#windows-setup)
- [Linux Setup](#linux-setup)
- [macOS Setup](#macos-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **CPU:** Any modern multi-core processor
- **RAM:** 8 GB (16 GB recommended)
- **Storage:** 10 GB free space for models and outputs
- **Python:** 3.10 or 3.11

### GPU Requirements (Recommended)
- **GPU:** NVIDIA GPU with CUDA support
  - Minimum: 6 GB VRAM (e.g., RTX 2060, GTX 1660 Ti)
  - Recommended: 12 GB VRAM (e.g., RTX 3060, RTX 4070)
  - Optimal: Multiple GPUs for parallel processing
- **CUDA:** Version 11.8 or 12.x
- **Compute Capability:** 7.0 or higher

### Tested Configurations
✅ **Windows 11 + Dual RTX 3060 (12GB each)** - Optimal
✅ **Ubuntu 22.04 + Single RTX 3080 (10GB)** - Excellent
✅ **Windows 10 + GTX 1660 Ti (6GB)** - Good (smaller models only)
⚠️ **macOS (any)** - CPU-only, slower performance

---

## Windows Setup

### 1. Install NVIDIA Drivers

1. Check your GPU model:
   - Press `Win + R`, type `devmgmt.msc`
   - Expand "Display adapters"

2. Download the latest driver:
   - Visit [NVIDIA Driver Downloads](https://www.nvidia.com/Download/index.aspx)
   - Select your GPU model
   - Download and install the **Game Ready Driver** or **Studio Driver**

3. Verify installation:
   ```powershell
   nvidia-smi
   ```
   You should see your GPU(s) listed with driver version.

### 2. Install FFmpeg

**Option A: Using Chocolatey (Recommended)**
```powershell
# Install Chocolatey if not already installed
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install FFmpeg
choco install ffmpeg
```

**Option B: Manual Installation**
1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html#build-windows)
2. Extract to `C:\ffmpeg`
3. Add to PATH:
   - Press `Win + R`, type `sysdm.cpl`, go to "Advanced" tab
   - Click "Environment Variables"
   - Under "System variables", edit "Path"
   - Add `C:\ffmpeg\bin`
   - Restart your terminal

**Verify FFmpeg:**
```powershell
ffmpeg -version
```

### 3. Install Python

1. Download Python 3.11 from [python.org](https://www.python.org/downloads/)
2. Run installer, check "Add Python to PATH"
3. Verify:
   ```powershell
   python --version
   ```

---

## Linux Setup

### 1. Install NVIDIA Drivers and CUDA Toolkit

**Ubuntu/Debian:**
```bash
# Update package list
sudo apt update

# Install NVIDIA driver
sudo apt install nvidia-driver-535

# Reboot
sudo reboot

# After reboot, verify
nvidia-smi

# Install CUDA Toolkit (optional, PyTorch includes CUDA runtime)
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install cuda-toolkit-12-2
```

**Fedora/RHEL:**
```bash
# Enable RPM Fusion repository
sudo dnf install https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm

# Install NVIDIA drivers
sudo dnf install akmod-nvidia
sudo dnf install xorg-x11-drv-nvidia-cuda

# Reboot
sudo reboot

# Verify
nvidia-smi
```

### 2. Install FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Fedora/RHEL:**
```bash
sudo dnf install ffmpeg
```

**Verify:**
```bash
ffmpeg -version
```

### 3. Install Python

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

**Fedora:**
```bash
sudo dnf install python3.11 python3.11-devel
```

**Verify:**
```bash
python3.11 --version
```

---

## macOS Setup

⚠️ **Note:** macOS does not support NVIDIA CUDA. TalkSmith will run in CPU-only mode, which is significantly slower.

### 1. Install FFmpeg

**Using Homebrew (Recommended):**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install FFmpeg
brew install ffmpeg
```

**Verify:**
```bash
ffmpeg -version
```

### 2. Install Python

**Using Homebrew:**
```bash
brew install python@3.11
```

**Verify:**
```bash
python3.11 --version
```

---

## Verification

After completing the setup for your platform, verify everything is working:

1. **Clone TalkSmith:**
   ```bash
   git clone https://github.com/DakotaIrsik/TalkSmith.git
   cd TalkSmith
   ```

2. **Install basic dependencies:**
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

3. **Run GPU verification:**
   ```bash
   python scripts/check_gpu.py
   ```

Expected output (with GPU):
```
======================================================================
  TalkSmith GPU Verification
======================================================================

----------------------------------------------------------------------
  System Information
----------------------------------------------------------------------

  ✓ Operating System              : Windows 11
  ✓ Architecture                  : AMD64
  ✓ Python Version                : 3.11.5

----------------------------------------------------------------------
  NVIDIA Driver
----------------------------------------------------------------------

  ✓ Driver Version                : 536.67
  ✓ nvidia-smi                    : Available

----------------------------------------------------------------------
  CUDA and PyTorch
----------------------------------------------------------------------

  ✓ PyTorch Version               : 2.1.0+cu118
  ✓ CUDA Available                : True
  ✓ CUDA Version                  : 11.8
  ✓ GPU Device Count              : 2

----------------------------------------------------------------------
  Detected GPU Devices
----------------------------------------------------------------------

  GPU 0:
    Name              : NVIDIA GeForce RTX 3060
    Total Memory      : 12.0 GB
    Compute Capability: 8.6

  GPU 1:
    Name              : NVIDIA GeForce RTX 3060
    Total Memory      : 12.0 GB
    Compute Capability: 8.6

----------------------------------------------------------------------
  GPU Functionality Test
----------------------------------------------------------------------

  ✓ Basic CUDA Operations         : PASSED

======================================================================
  Summary
======================================================================

  ✓ All checks passed!
  ✓ 2 GPU(s) detected and operational
  ✓ TalkSmith is ready for GPU-accelerated transcription

  🚀 Multi-GPU setup detected (2 GPUs)
     You can use multi-GPU parallelism features!
```

---

## Troubleshooting

### Common CUDA Errors

#### Error: `CUDA driver version is insufficient for CUDA runtime version`
**Cause:** PyTorch CUDA version is newer than your installed NVIDIA driver.

**Solution:**
1. Check your driver version: `nvidia-smi`
2. Install matching PyTorch version:
   ```bash
   # For CUDA 11.8
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

   # For CUDA 12.1
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

#### Error: `CUDA out of memory (OOM)`
**Cause:** Model or batch size too large for your GPU's VRAM.

**Solutions:**
1. Use a smaller Whisper model:
   - Change `whisper_model = medium.en` in `config/settings.ini`
   - Available: `tiny`, `base`, `small`, `medium`, `large-v3`

2. Reduce batch size in `config/settings.ini`:
   ```ini
   [Models]
   batch_size = 8  # Reduce from 16
   ```

3. Use compute_type optimization:
   ```ini
   [Models]
   compute_type = int8  # Reduce from float16
   ```

#### Error: `torch.cuda.is_available()` returns `False`
**Cause:** PyTorch not installed with CUDA support or driver issues.

**Solutions:**
1. Reinstall PyTorch with CUDA:
   ```bash
   pip uninstall torch torchvision torchaudio
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

2. Verify NVIDIA driver: `nvidia-smi`
3. Restart your system after driver installation

#### Error: GPU not detected in multi-GPU setup
**Cause:** GPUs not visible to CUDA or PCIe issues.

**Solutions:**
1. Check both GPUs in Device Manager (Windows) or `lspci` (Linux)
2. Ensure both GPUs have power connectors properly seated
3. Update motherboard BIOS
4. Check BIOS settings for PCIe configuration
5. Try GPUs in different PCIe slots

### Out-of-Memory Fragmentation

**Symptom:** CUDA OOM error even with available VRAM.

**Solution:**
```python
# Clear CUDA cache before processing
import torch
torch.cuda.empty_cache()
```

TalkSmith handles this automatically, but you can manually clear cache:
```bash
python -c "import torch; torch.cuda.empty_cache(); print('Cache cleared')"
```

### FFmpeg Not Found

**Symptom:** `ffmpeg: command not found` or similar error.

**Solutions:**
1. Verify FFmpeg is installed: `ffmpeg -version`
2. Check PATH includes FFmpeg location
3. Restart terminal after installation
4. On Windows, restart PowerShell/Command Prompt

### Performance Issues

#### Slow Transcription (High RTF)
**Causes & Solutions:**

1. **CPU mode instead of GPU:**
   - Run `python scripts/check_gpu.py`
   - Ensure CUDA is available

2. **Wrong model size:**
   - Larger models (`large-v3`) are slower
   - Use `medium.en` for English-only content

3. **Insufficient VRAM:**
   - Monitor with `nvidia-smi` during processing
   - Reduce batch size or model size

4. **Background GPU usage:**
   - Close other GPU-intensive applications
   - Check `nvidia-smi` for other processes

---

## Next Steps

Once verification passes:
1. Proceed to [environment setup](../README.md#planned-installation)
2. Review [configuration options](configuration.md)
3. Try the [Quick Start guide](../README.md#planned-basic-usage)

For additional help:
- 📖 [Main README](../README.md)
- 🐛 [GitHub Issues](https://github.com/DakotaIrsik/TalkSmith/issues)
- 💬 [GitHub Discussions](https://github.com/DakotaIrsik/TalkSmith/discussions)
