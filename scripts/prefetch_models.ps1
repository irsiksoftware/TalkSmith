<#
.SYNOPSIS
    Prefetch Whisper and diarization models for TalkSmith

.DESCRIPTION
    Downloads and caches Whisper models and pyannote diarization models.
    This script helps ensure models are available offline and reduces
    first-run latency.

.PARAMETER Sizes
    Comma-separated list of Whisper model sizes to download.
    Available: tiny, tiny.en, base, base.en, small, small.en, medium, medium.en, large-v2, large-v3
    Default: medium.en,large-v3

.PARAMETER CacheDir
    Directory to store model cache. Default: .cache

.PARAMETER SkipDiarization
    Skip downloading diarization models (requires HuggingFace token)

.PARAMETER HfToken
    HuggingFace token for downloading pyannote models (optional if already configured)

.EXAMPLE
    .\scripts\prefetch_models.ps1
    Downloads default models (medium.en, large-v3)

.EXAMPLE
    .\scripts\prefetch_models.ps1 -Sizes "medium.en,large-v3" -SkipDiarization
    Downloads specific Whisper models only

.EXAMPLE
    .\scripts\prefetch_models.ps1 -HfToken "hf_xxx"
    Downloads models with HuggingFace authentication

.NOTES
    Model sizes (approximate disk space):
    - tiny/tiny.en: ~75 MB
    - base/base.en: ~150 MB
    - small/small.en: ~500 MB
    - medium/medium.en: ~1.5 GB
    - large-v2: ~3 GB
    - large-v3: ~3 GB
    - pyannote diarization: ~100 MB
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$Sizes = "medium.en,large-v3",

    [Parameter(Mandatory=$false)]
    [string]$CacheDir = ".cache",

    [Parameter(Mandatory=$false)]
    [switch]$SkipDiarization,

    [Parameter(Mandatory=$false)]
    [string]$HfToken = ""
)

$ErrorActionPreference = "Stop"

# Display header
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "TalkSmith Model Prefetch Utility" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Parse sizes
$modelSizes = $Sizes -split ","
$validSizes = @("tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large-v2", "large-v3")

# Validate sizes
foreach ($size in $modelSizes) {
    if ($size -notin $validSizes) {
        Write-Host "Error: Invalid model size '$size'" -ForegroundColor Red
        Write-Host "Valid sizes: $($validSizes -join ', ')" -ForegroundColor Yellow
        exit 1
    }
}

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.10 or 3.11" -ForegroundColor Red
    exit 1
}

# Create cache directory
if (-not (Test-Path $CacheDir)) {
    New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null
    Write-Host "✓ Created cache directory: $CacheDir" -ForegroundColor Green
} else {
    Write-Host "✓ Cache directory exists: $CacheDir" -ForegroundColor Green
}

# Set environment variable for HuggingFace cache
$env:HF_HOME = $CacheDir
$env:TRANSFORMERS_CACHE = "$CacheDir\transformers"

Write-Host ""
Write-Host "Downloading Whisper models..." -ForegroundColor Cyan
Write-Host ""

# Download Whisper models
foreach ($size in $modelSizes) {
    Write-Host "Downloading Whisper model: $size" -ForegroundColor Yellow

    $pythonScript = @"
import sys
try:
    from faster_whisper import WhisperModel

    # Download model by initializing it
    model = WhisperModel("$size", device="cpu", download_root="$CacheDir")
    print(f"✓ Successfully downloaded: $size")
    sys.exit(0)
except ImportError:
    print("Error: faster-whisper not installed. Run: pip install faster-whisper")
    sys.exit(1)
except Exception as e:
    print(f"Error downloading $size: {e}")
    sys.exit(1)
"@

    $tempFile = New-TemporaryFile
    $pythonScript | Out-File -FilePath $tempFile.FullName -Encoding UTF8

    try {
        python $tempFile.FullName
        if ($LASTEXITCODE -ne 0) {
            Write-Host "✗ Failed to download: $size" -ForegroundColor Red
        } else {
            Write-Host "✓ Successfully cached: $size" -ForegroundColor Green
        }
    } finally {
        Remove-Item $tempFile.FullName -Force
    }

    Write-Host ""
}

# Download diarization models
if (-not $SkipDiarization) {
    Write-Host "Downloading diarization models..." -ForegroundColor Cyan
    Write-Host ""

    # Set HF token if provided
    if ($HfToken) {
        $env:HF_TOKEN = $HfToken
        Write-Host "✓ Using provided HuggingFace token" -ForegroundColor Green
    } elseif ($env:HF_TOKEN) {
        Write-Host "✓ Using HuggingFace token from environment" -ForegroundColor Green
    } else {
        Write-Host "⚠ No HuggingFace token provided. Diarization download may fail." -ForegroundColor Yellow
        Write-Host "  Get a token at: https://huggingface.co/settings/tokens" -ForegroundColor Yellow
        Write-Host "  Accept terms at: https://huggingface.co/pyannote/speaker-diarization-3.1" -ForegroundColor Yellow
        Write-Host ""
    }

    $pythonScript = @"
import sys
import os

try:
    from pyannote.audio import Pipeline

    # Set cache directory
    os.environ['HF_HOME'] = "$CacheDir"

    # Download diarization pipeline
    model_name = "pyannote/speaker-diarization-3.1"
    pipeline = Pipeline.from_pretrained(model_name)
    print(f"✓ Successfully downloaded: {model_name}")
    sys.exit(0)

except ImportError:
    print("Error: pyannote.audio not installed. Run: pip install pyannote.audio")
    sys.exit(1)
except Exception as e:
    print(f"Error downloading diarization model: {e}")
    print("\nMake sure you:")
    print("1. Have a HuggingFace token: https://huggingface.co/settings/tokens")
    print("2. Accepted terms: https://huggingface.co/pyannote/speaker-diarization-3.1")
    print("3. Set HF_TOKEN environment variable or pass -HfToken parameter")
    sys.exit(1)
"@

    $tempFile = New-TemporaryFile
    $pythonScript | Out-File -FilePath $tempFile.FullName -Encoding UTF8

    try {
        python $tempFile.FullName
        if ($LASTEXITCODE -ne 0) {
            Write-Host "✗ Failed to download diarization models" -ForegroundColor Red
            Write-Host "  Use -SkipDiarization flag to skip diarization model download" -ForegroundColor Yellow
        } else {
            Write-Host "✓ Successfully cached diarization models" -ForegroundColor Green
        }
    } finally {
        Remove-Item $tempFile.FullName -Force
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Model prefetch complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Models cached in: $CacheDir" -ForegroundColor White
Write-Host "To use these models, ensure TRANSFORMERS_CACHE=$CacheDir\transformers" -ForegroundColor White
Write-Host ""
