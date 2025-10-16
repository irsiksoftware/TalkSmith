#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Batch transcribe audio files using TalkSmith.

.DESCRIPTION
    Processes all audio files in an input directory with resume capability.

.PARAMETER InputDir
    Input directory containing audio files (default: data/inputs)

.PARAMETER OutputDir
    Output directory for transcriptions (default: data/outputs)

.PARAMETER ModelSize
    Whisper model size: tiny, base, small, medium, medium.en, large-v3 (default: base)

.PARAMETER Device
    Device to use: cuda or cpu (default: cuda)

.PARAMETER Diarization
    Diarization mode: whisperx, alt, or off (default: off)

.PARAMETER Preprocess
    Enable audio preprocessing

.EXAMPLE
    .\batch_transcribe.ps1 -ModelSize large-v3
    .\batch_transcribe.ps1 -InputDir "C:\audio" -OutputDir "C:\output" -Diarization whisperx
#>

param(
    [string]$InputDir = "data/inputs",
    [string]$OutputDir = "data/outputs",
    [ValidateSet("tiny", "base", "small", "medium", "medium.en", "large-v3")]
    [string]$ModelSize = "base",
    [ValidateSet("cuda", "cpu")]
    [string]$Device = "cuda",
    [ValidateSet("whisperx", "alt", "off")]
    [string]$Diarization = "off",
    [switch]$Preprocess
)

$ErrorActionPreference = "Stop"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

# Change to root directory
Push-Location $RootDir

try {
    # Build arguments
    $args = @(
        "$ScriptDir\batch_transcribe.py",
        "--input-dir", $InputDir,
        "--output-dir", $OutputDir,
        "--model-size", $ModelSize,
        "--device", $Device,
        "--diarization", $Diarization
    )

    if ($Preprocess) {
        $args += "--preprocess"
    }

    # Run batch transcribe
    python @args

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Batch transcription failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
