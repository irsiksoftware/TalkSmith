#!/bin/bash
# TalkSmith Environment Setup Script for Linux/macOS
# Bash script to create and activate Python environment

set -e

ENV_TYPE="${1:-venv}"  # "venv" or "conda"
PYTHON_VERSION="${2:-3.11}"
CUDA_VERSION="${3:-cu118}"  # cu118, cu121, or cpu

echo "========================================"
echo "  TalkSmith Environment Setup"
echo "========================================"
echo ""

# Check if we're in the TalkSmith directory
if [ ! -f "config/settings.ini" ]; then
    echo "Error: Please run this script from the TalkSmith root directory"
    exit 1
fi

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

if [ "$ENV_TYPE" = "conda" ]; then
    echo "[1/5] Checking for Conda..."

    if ! command_exists conda; then
        echo "Error: Conda not found. Please install Miniconda or Anaconda:"
        echo "  https://docs.conda.io/en/latest/miniconda.html"
        exit 1
    fi

    echo "  ✓ Found: $(conda --version)"

    echo ""
    echo "[2/5] Creating Conda environment..."
    conda env create -f environment.yml --force

    echo ""
    echo "[3/5] Activating environment..."
    echo "  Run: conda activate talksmith"

    echo ""
    echo "[4/5] Verifying installation..."
    conda run -n talksmith python --version

    echo ""
    echo "[5/5] Testing CUDA availability..."
    conda run -n talksmith python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"

else
    echo "[1/6] Checking for Python..."

    PYTHON_CMD="python$PYTHON_VERSION"
    if ! command_exists "$PYTHON_CMD"; then
        PYTHON_CMD="python3"
        if ! command_exists "$PYTHON_CMD"; then
            PYTHON_CMD="python"
            if ! command_exists "$PYTHON_CMD"; then
                echo "Error: Python not found. Please install Python $PYTHON_VERSION"
                exit 1
            fi
        fi
    fi

    INSTALLED_VERSION=$($PYTHON_CMD --version)
    echo "  ✓ Found: $INSTALLED_VERSION"

    echo ""
    echo "[2/6] Creating virtual environment..."
    $PYTHON_CMD -m venv venv

    if [ ! -f "venv/bin/activate" ]; then
        echo "Error: Failed to create virtual environment"
        exit 1
    fi

    echo ""
    echo "[3/6] Activating virtual environment..."
    source venv/bin/activate

    echo ""
    echo "[4/6] Upgrading pip..."
    python -m pip install --upgrade pip setuptools wheel

    echo ""
    echo "[5/6] Installing PyTorch with CUDA..."
    if [ "$CUDA_VERSION" = "cpu" ]; then
        echo "  Installing CPU-only version..."
        pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    else
        echo "  Installing CUDA $CUDA_VERSION version..."
        pip install torch torchaudio --index-url "https://download.pytorch.org/whl/$CUDA_VERSION"
    fi

    echo ""
    echo "[6/6] Installing TalkSmith dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "========================================"
echo "  Verification Steps"
echo "========================================"

echo ""
echo "[1/3] Verifying FFmpeg installation..."
if command_exists ffmpeg; then
    FFMPEG_VERSION=$(ffmpeg -version 2>&1 | head -n 1)
    echo "  ✓ Found: $FFMPEG_VERSION"
else
    echo "  ✗ Warning: FFmpeg not found in PATH"
    echo "  Please install FFmpeg:"
    echo "    Linux:  sudo apt install ffmpeg"
    echo "    macOS:  brew install ffmpeg"
    echo "    Or visit: https://ffmpeg.org/download.html"
fi

echo ""
echo "[2/3] Verifying CUDA availability..."
if [ "$ENV_TYPE" = "conda" ]; then
    conda run -n talksmith python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"
else
    python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"
fi

echo ""
echo "[3/3] Testing basic imports..."
TEST_SCRIPT='
try:
    import numpy as np
    print("  numpy: OK")
    import torch
    print("  torch: OK")
    import librosa
    print("  librosa: OK")
    import resemblyzer
    print("  resemblyzer: OK")
    import sklearn
    print("  sklearn: OK")
    print("\nAll imports successful!")
except ImportError as e:
    print(f"  Import error: {e}")
    exit(1)
'

if [ "$ENV_TYPE" = "conda" ]; then
    conda run -n talksmith python -c "$TEST_SCRIPT"
else
    python -c "$TEST_SCRIPT"
fi

echo ""
echo "========================================"
echo "  ✓ Environment Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"

if [ "$ENV_TYPE" = "conda" ]; then
    echo "  1. Activate: conda activate talksmith"
else
    echo "  1. Activate: source venv/bin/activate"
fi

echo "  2. Verify GPU: python scripts/check_gpu.py"
echo "  3. Verify FFmpeg: python scripts/check_ffmpeg.py"
echo "  4. See README.md for usage examples"
echo ""
