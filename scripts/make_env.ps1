# TalkSmith Environment Setup Script for Windows
# PowerShell script to create and activate Python environment

param(
    [string]$EnvType = "venv",  # "venv" or "conda"
    [string]$PythonVersion = "3.11",
    [string]$CudaVersion = "cu118"  # cu118, cu121, or cpu
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TalkSmith Environment Setup (Windows)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the TalkSmith directory
if (-Not (Test-Path "config\settings.ini")) {
    Write-Host "Error: Please run this script from the TalkSmith root directory" -ForegroundColor Red
    exit 1
}

function Test-CommandExists {
    param($Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

if ($EnvType -eq "conda") {
    Write-Host "[1/5] Checking for Conda..." -ForegroundColor Yellow

    if (-Not (Test-CommandExists "conda")) {
        Write-Host "Error: Conda not found. Please install Miniconda or Anaconda:" -ForegroundColor Red
        Write-Host "  https://docs.conda.io/en/latest/miniconda.html" -ForegroundColor Red
        exit 1
    }

    Write-Host "  Found: $(conda --version)" -ForegroundColor Green

    Write-Host "`n[2/5] Creating Conda environment..." -ForegroundColor Yellow
    conda env create -f environment.yml --force

    Write-Host "`n[3/5] Activating environment..." -ForegroundColor Yellow
    Write-Host "  Run: conda activate talksmith" -ForegroundColor Cyan

    Write-Host "`n[4/5] Verifying installation..." -ForegroundColor Yellow
    & conda run -n talksmith python --version

    Write-Host "`n[5/5] Testing CUDA availability..." -ForegroundColor Yellow
    & conda run -n talksmith python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"

} else {
    Write-Host "[1/6] Checking for Python..." -ForegroundColor Yellow

    $PythonCmd = "python"
    if (Test-CommandExists "python$PythonVersion") {
        $PythonCmd = "python$PythonVersion"
    } elseif (-Not (Test-CommandExists "python")) {
        Write-Host "Error: Python not found. Please install Python $PythonVersion:" -ForegroundColor Red
        Write-Host "  https://www.python.org/downloads/" -ForegroundColor Red
        exit 1
    }

    $InstalledVersion = & $PythonCmd --version
    Write-Host "  Found: $InstalledVersion" -ForegroundColor Green

    Write-Host "`n[2/6] Creating virtual environment..." -ForegroundColor Yellow
    & $PythonCmd -m venv venv

    if (-Not (Test-Path "venv\Scripts\Activate.ps1")) {
        Write-Host "Error: Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }

    Write-Host "`n[3/6] Activating virtual environment..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"

    Write-Host "`n[4/6] Upgrading pip..." -ForegroundColor Yellow
    & python -m pip install --upgrade pip setuptools wheel

    Write-Host "`n[5/6] Installing PyTorch with CUDA..." -ForegroundColor Yellow
    if ($CudaVersion -eq "cpu") {
        Write-Host "  Installing CPU-only version..." -ForegroundColor Cyan
        & pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    } else {
        Write-Host "  Installing CUDA $CudaVersion version..." -ForegroundColor Cyan
        & pip install torch torchaudio --index-url "https://download.pytorch.org/whl/$CudaVersion"
    }

    Write-Host "`n[6/6] Installing TalkSmith dependencies..." -ForegroundColor Yellow
    & pip install -r requirements.txt

    Write-Host "`nVerifying CUDA availability..." -ForegroundColor Yellow
    & python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')"
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Environment Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan

if ($EnvType -eq "conda") {
    Write-Host "  1. Activate: conda activate talksmith" -ForegroundColor White
} else {
    Write-Host "  1. Activate: .\venv\Scripts\Activate.ps1" -ForegroundColor White
}

Write-Host "  2. Verify GPU: python scripts\check_gpu.py" -ForegroundColor White
Write-Host "  3. Verify FFmpeg: python scripts\check_ffmpeg.py" -ForegroundColor White
Write-Host "  4. See README.md for usage examples" -ForegroundColor White
Write-Host ""
