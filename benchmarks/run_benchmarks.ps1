#
# TalkSmith Benchmark Suite Runner (PowerShell)
# Tests multiple model configurations for RTF and WER metrics
#

param(
    [switch]$Quick,
    [switch]$Full,
    [string[]]$Models,
    [string[]]$Devices,
    [string]$Output = ".\benchmarks\results",
    [switch]$Help
)

# Show help
if ($Help) {
    Write-Host @"
Usage: .\run_benchmarks.ps1 [OPTIONS]

Options:
  -Quick            Run quick benchmark (tiny model, 1min sample only)
  -Full             Run full benchmark suite (all models, all samples)
  -Models MODEL1,MODEL2  Comma-separated list of models to test
  -Devices DEV1,DEV2     Comma-separated list of devices (cuda,cpu)
  -Output DIR       Output directory for results (default: .\benchmarks\results)
  -Help             Show this help message

Examples:
  .\run_benchmarks.ps1 -Quick                    # Fast test on small sample
  .\run_benchmarks.ps1 -Full                     # Complete benchmark suite
  .\run_benchmarks.ps1 -Models tiny,base         # Test only tiny and base models
  .\run_benchmarks.ps1 -Devices cuda             # Test only on GPU
"@
    exit 0
}

# Default configuration
$AllModels = @("tiny", "base", "small", "medium", "large-v3")
$AllDevices = @("cuda", "cpu")
$AllComputeTypes = @("float16", "int8")
$AllDiarizationOpts = @($true, $false)
$TestAudioDir = ".\benchmarks\test_audio"
$GroundTruth = "$TestAudioDir\ground_truth.json"

# Configure based on mode
if ($Quick) {
    $TestFiles = @("sample_1min.wav")
    $Models = @("tiny")
    $Devices = @("cuda")
    $AllComputeTypes = @("float16")
    $AllDiarizationOpts = @($false)
    Write-Host "Running QUICK benchmark mode" -ForegroundColor Yellow
} elseif ($Full) {
    $TestFiles = @("sample_1min.wav", "sample_5min.wav", "sample_30min.wav")
    if (-not $Models) { $Models = $AllModels }
    if (-not $Devices) { $Devices = $AllDevices }
    Write-Host "Running FULL benchmark mode" -ForegroundColor Yellow
} else {
    $TestFiles = @("sample_1min.wav", "sample_5min.wav")
    if (-not $Models) { $Models = $AllModels }
    if (-not $Devices) { $Devices = $AllDevices }
    Write-Host "Running STANDARD benchmark mode" -ForegroundColor Yellow
}

# Create output directory
New-Item -ItemType Directory -Force -Path $Output | Out-Null
$ResultsFile = Join-Path $Output "benchmark_results.jsonl"

# Clear previous results
if (Test-Path $ResultsFile) {
    Remove-Item $ResultsFile
}
New-Item -ItemType File -Path $ResultsFile | Out-Null

Write-Host ""
Write-Host "TalkSmith Benchmark Suite" -ForegroundColor Blue
Write-Host "================================"
Write-Host "Output directory: $Output"
Write-Host "Test files: $($TestFiles -join ', ')"
Write-Host "Models: $($Models -join ', ')"
Write-Host "Devices: $($Devices -join ', ')"
Write-Host ""

# Check if test audio files exist
$MissingFiles = 0
foreach ($file in $TestFiles) {
    $fullPath = Join-Path $TestAudioDir $file
    if (-not (Test-Path $fullPath)) {
        Write-Host "Warning: Test file not found: $fullPath" -ForegroundColor Red
        Write-Host "Please add test audio files to $TestAudioDir" -ForegroundColor Yellow
        $MissingFiles++
    }
}

if ($MissingFiles -gt 0) {
    Write-Host "Missing $MissingFiles test file(s). Exiting." -ForegroundColor Red
    exit 1
}

# Check if ground truth exists
if (-not (Test-Path $GroundTruth)) {
    Write-Host "Warning: Ground truth file not found: $GroundTruth" -ForegroundColor Yellow
    Write-Host "WER calculation will be skipped" -ForegroundColor Yellow
}

# Calculate total tests
$TotalTests = 0
foreach ($model in $Models) {
    foreach ($device in $Devices) {
        foreach ($compute in $AllComputeTypes) {
            foreach ($diarize in $AllDiarizationOpts) {
                foreach ($file in $TestFiles) {
                    $TotalTests++
                }
            }
        }
    }
}

Write-Host "Total benchmark configurations: $TotalTests" -ForegroundColor Blue
Write-Host ""

# Run benchmarks
$CompletedTests = 0

foreach ($model in $Models) {
    foreach ($device in $Devices) {
        foreach ($compute in $AllComputeTypes) {
            foreach ($diarize in $AllDiarizationOpts) {
                foreach ($file in $TestFiles) {
                    $CompletedTests++

                    # Skip CPU + float16 (not supported)
                    if ($device -eq "cpu" -and $compute -eq "float16") {
                        Write-Host "[$CompletedTests/$TotalTests] Skipping: $model/$device/$compute (unsupported)" -ForegroundColor Yellow
                        continue
                    }

                    $diarizeLabel = if ($diarize) { "yes" } else { "no" }
                    Write-Host "[$CompletedTests/$TotalTests] Testing: $model / $device / $compute / diarization=$diarizeLabel / $file" -ForegroundColor Green

                    # Build command
                    $inputFile = Join-Path $TestAudioDir $file
                    $outputFile = Join-Path $Output "$($model)_$($device)_$($compute)_diarize$($diarizeLabel)_$([System.IO.Path]::GetFileNameWithoutExtension($file)).json"

                    # Run transcription
                    $startTime = Get-Date

                    $diarizeArg = if ($diarize) { "--diarize" } else { "" }
                    $logFile = Join-Path $Output "run.log"

                    $arguments = @(
                        "pipeline\transcribe_fw.py",
                        "--audio", $inputFile,
                        "--model", $model,
                        "--device", $device,
                        "--compute_type", $compute,
                        "--output", $outputFile
                    )

                    if ($diarize) {
                        $arguments += "--diarize"
                    }

                    try {
                        python @arguments > $logFile 2>&1
                        $exitCode = $LASTEXITCODE
                    } catch {
                        Write-Host "  Error running benchmark: $_" -ForegroundColor Red
                        continue
                    }

                    if ($exitCode -ne 0) {
                        Write-Host "  Error running benchmark. Check $logFile" -ForegroundColor Red
                        continue
                    }

                    $endTime = Get-Date
                    $processTime = ($endTime - $startTime).TotalSeconds

                    # Extract metrics from output
                    if (Test-Path $outputFile) {
                        $logContent = Get-Content $logFile -Raw

                        # Parse audio duration and RTF from log
                        $audioDuration = 0
                        $rtf = 0

                        if ($logContent -match 'Audio duration:\s*([\d.]+)') {
                            $audioDuration = [double]$matches[1]
                        }

                        if ($logContent -match 'RTF:\s*([\d.]+)') {
                            $rtf = [double]$matches[1]
                        } elseif ($audioDuration -gt 0) {
                            $rtf = $processTime / $audioDuration
                        }

                        # Store result
                        $result = @{
                            model = $model
                            device = $device
                            compute_type = $compute
                            diarization = $diarize
                            audio_file = $file
                            audio_duration = $audioDuration
                            process_time = $processTime
                            rtf = $rtf
                            output_file = $outputFile
                            timestamp = (Get-Date -Format o)
                        } | ConvertTo-Json -Compress

                        Add-Content -Path $ResultsFile -Value $result

                        Write-Host "  RTF: $($rtf.ToString('F3')) | Process time: $($processTime.ToString('F2'))s" -ForegroundColor Blue
                    } else {
                        Write-Host "  Error: Output file not created" -ForegroundColor Red
                    }

                    Write-Host ""
                }
            }
        }
    }
}

Write-Host "Benchmark suite completed!" -ForegroundColor Green
Write-Host ""
Write-Host "Results saved to: $ResultsFile"
Write-Host ""

# Generate reports using Python
Write-Host "Generating reports..." -ForegroundColor Blue

$pythonScript = @"
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from benchmarks.metrics import BenchmarkResult, generate_report, load_ground_truth, calculate_wer

# Load results
results = []
with open('$($ResultsFile.Replace('\', '/'))', 'r') as f:
    for line in f:
        if line.strip():
            data = json.loads(line)

            # Try to load transcript and calculate WER
            wer = None
            if Path('$($GroundTruth.Replace('\', '/'))').exists():
                try:
                    ground_truth = load_ground_truth(Path('$($GroundTruth.Replace('\', '/'))'))
                    if data['audio_file'] in ground_truth:
                        # Load hypothesis from output file
                        with open(data['output_file'], 'r') as tf:
                            transcript_data = json.load(tf)
                            hypothesis = transcript_data.get('text', '')

                        reference = ground_truth[data['audio_file']]
                        wer = calculate_wer(reference, hypothesis)
                except Exception as e:
                    print(f"Warning: Could not calculate WER: {e}", file=sys.stderr)

            result = BenchmarkResult(
                model=data['model'],
                device=data['device'],
                compute_type=data['compute_type'],
                diarization=data['diarization'],
                audio_file=data['audio_file'],
                audio_duration=float(data['audio_duration']),
                process_time=float(data['process_time']),
                rtf=float(data['rtf']),
                wer=wer,
                memory_mb=None,
                timestamp=data['timestamp']
            )
            results.append(result)

# Generate reports
generate_report(results, Path('$($Output.Replace('\', '/'))'))

print(f"\n✓ Reports generated in $Output/")
print(f"  - report.csv (machine-readable)")
print(f"  - report.json (detailed metrics)")
print(f"  - report.md (human-readable summary)")
"@

$pythonScript | python -

Write-Host ""
Write-Host "Done! Check $Output\report.md for results." -ForegroundColor Green
