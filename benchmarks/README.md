# TalkSmith Benchmark Suite

Automated benchmark suite for measuring transcription performance across models and configurations.

## Quick Start

```bash
# Linux/Mac
./run_benchmarks.sh --quick

# Windows
.\run_benchmarks.ps1 -Quick
```

## What This Measures

- **RTF (Real-Time Factor)**: Processing speed
  - RTF < 1.0 = faster than real-time
  - RTF = 1.0 = real-time processing
  - RTF > 1.0 = slower than real-time

- **WER (Word Error Rate)**: Transcription accuracy
  - WER = 0.0 = perfect accuracy
  - WER = 0.05 = 5% error rate

## Files

- `metrics.py` - Core metrics calculation (RTF, WER, reporting)
- `run_benchmarks.sh` - Benchmark runner for Linux/Mac
- `run_benchmarks.ps1` - Benchmark runner for Windows
- `test_audio/` - Test audio files and ground truth transcripts
- `results/` - Output directory (generated after running benchmarks)

## Prerequisites

1. **Install dependencies**:

   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Add test audio files** to `test_audio/`:
   - `sample_1min.wav` (required for quick benchmarks)
   - `sample_5min.wav` (recommended)
   - `sample_30min.wav` (optional, for full benchmarks)

3. **Edit ground truth transcripts** in `test_audio/ground_truth.json`:

   ```json
   {
     "sample_1min.wav": "Your reference transcript here...",
     "sample_5min.wav": "Another reference transcript..."
   }
   ```

## Usage

### Linux/Mac

```bash
# Quick benchmark (tiny model only)
./run_benchmarks.sh --quick

# Standard benchmark (common models)
./run_benchmarks.sh

# Full benchmark (all models and configurations)
./run_benchmarks.sh --full

# Custom configuration
./run_benchmarks.sh --models tiny,base,small --devices cuda
```

### Windows

```powershell
# Quick benchmark
.\run_benchmarks.ps1 -Quick

# Standard benchmark
.\run_benchmarks.ps1

# Full benchmark
.\run_benchmarks.ps1 -Full

# Custom configuration
.\run_benchmarks.ps1 -Models tiny,base,small -Devices cuda
```

## Output Files

Results are saved to `results/`:

- `report.md` - Human-readable summary with tables
- `report.csv` - Machine-readable data for analysis
- `report.json` - Complete metrics in JSON format

## Configuration Options

### Models

- `tiny` - Fastest, lowest accuracy
- `base` - Good balance
- `small` - Better accuracy
- `medium` - High accuracy
- `large-v3` - Highest accuracy

### Devices

- `cuda` - GPU acceleration (requires CUDA)
- `cpu` - CPU-only processing

### Compute Types

- `float16` - Fast, GPU-only
- `int8` - Quantized, CPU/GPU compatible

## Using the Metrics Module

```python
from benchmarks.metrics import calculate_rtf, calculate_wer

# Calculate RTF
rtf = calculate_rtf(audio_duration=300, process_time=45)
print(f"RTF: {rtf:.3f}")  # 0.150

# Calculate WER
wer = calculate_wer(
    reference="The quick brown fox",
    hypothesis="The quick brown fox"
)
print(f"WER: {wer:.2%}")  # 0.00%
```

## Documentation

See `../docs/benchmarking.md` for complete documentation including:

- Detailed usage guide
- Understanding metrics
- CI/CD integration
- Advanced analysis examples
- Troubleshooting

## Support

For issues or questions, see the [main README](../README.md) or open an issue on GitHub.
