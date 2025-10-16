# TalkSmith Benchmarking Guide

This document describes how to use the TalkSmith benchmark suite to measure transcription performance across different models and configurations.

## Overview

The benchmark suite measures two key metrics:
- **RTF (Real-Time Factor)**: Speed of transcription (lower is better)
  - RTF < 1.0 = faster than real-time
  - RTF = 1.0 = real-time processing
  - RTF > 1.0 = slower than real-time
- **WER (Word Error Rate)**: Accuracy of transcription (lower is better)
  - WER = 0.0 = perfect transcription
  - WER = 0.05 = 5% error rate
  - WER = 1.0 = completely incorrect

## Quick Start

### Prerequisites

1. **Test Audio Files**: Place audio files in `benchmarks/test_audio/`:
   - `sample_1min.wav` - 1-minute sample
   - `sample_5min.wav` - 5-minute sample
   - `sample_30min.wav` - 30-minute sample (optional, for full benchmarks)

2. **Ground Truth Transcripts**: Edit `benchmarks/test_audio/ground_truth.json` with reference transcripts:
   ```json
   {
     "sample_1min.wav": "The actual spoken words in the audio file...",
     "sample_5min.wav": "Another reference transcript...",
     "sample_30min.wav": "Optional third transcript..."
   }
   ```

### Running Benchmarks

#### Linux/Mac

```bash
# Quick benchmark (tiny model, 1min sample only)
cd benchmarks
./run_benchmarks.sh --quick

# Standard benchmark (all models, 1min + 5min samples)
./run_benchmarks.sh

# Full benchmark (all models, all samples)
./run_benchmarks.sh --full

# Custom configuration
./run_benchmarks.sh --models tiny,base,small --devices cuda
```

#### Windows

```powershell
# Quick benchmark
cd benchmarks
.\run_benchmarks.ps1 -Quick

# Standard benchmark
.\run_benchmarks.ps1

# Full benchmark
.\run_benchmarks.ps1 -Full

# Custom configuration
.\run_benchmarks.ps1 -Models tiny,base,small -Devices cuda
```

## Command-Line Options

### Bash (Linux/Mac)

```
--quick              Run quick benchmark (tiny model, 1min sample only)
--full               Run full benchmark suite (all models, all samples)
--models M1,M2       Comma-separated list of models to test
--devices D1,D2      Comma-separated list of devices (cuda,cpu)
--output DIR         Output directory for results
--help               Show help message
```

### PowerShell (Windows)

```
-Quick               Run quick benchmark (tiny model, 1min sample only)
-Full                Run full benchmark suite (all models, all samples)
-Models M1,M2        Comma-separated list of models to test
-Devices D1,D2       Comma-separated list of devices (cuda,cpu)
-Output DIR          Output directory for results
-Help                Show help message
```

## Output Files

After running benchmarks, results are saved to `benchmarks/results/`:

### 1. `report.md` - Human-Readable Summary

Markdown report with:
- Summary statistics
- Detailed results by audio file
- Best configurations (fastest, most accurate)
- Speed vs accuracy trade-off analysis

Example:
```markdown
# TalkSmith Benchmark Report

## Summary Statistics
- Total Benchmarks: 15
- Models Tested: tiny, base, small, medium, large-v3
- Devices: cuda, cpu

## Detailed Results

### sample_5min.wav

| Model | Device | RTF | WER | Process Time |
|-------|--------|-----|-----|--------------|
| tiny  | cuda   | 0.05| 12% | 15s          |
| base  | cuda   | 0.08| 8%  | 24s          |
...
```

### 2. `report.csv` - Machine-Readable Results

CSV file with all metrics for further analysis:
```csv
model,device,compute_type,diarization,audio_file,audio_duration,process_time,rtf,wer,memory_mb,timestamp
tiny,cuda,float16,False,sample_1min.wav,60.0,3.2,0.053,0.12,2048,2025-10-16T...
```

### 3. `report.json` - Detailed Metrics

JSON file with complete benchmark data:
```json
[
  {
    "model": "tiny",
    "device": "cuda",
    "compute_type": "float16",
    "diarization": false,
    "audio_file": "sample_1min.wav",
    "audio_duration": 60.0,
    "process_time": 3.2,
    "rtf": 0.053,
    "wer": 0.12,
    "memory_mb": 2048,
    "timestamp": "2025-10-16T12:34:56"
  }
]
```

## Model Configurations

The benchmark suite tests these configurations:

### Models
- `tiny` - Fastest, lowest accuracy
- `base` - Good balance for quick transcription
- `small` - Better accuracy, moderate speed
- `medium` - High accuracy, slower
- `large-v3` - Highest accuracy, slowest

### Devices
- `cuda` - GPU acceleration (requires CUDA-compatible GPU)
- `cpu` - CPU-only processing

### Compute Types
- `float16` - Fast, GPU-only (CUDA)
- `int8` - Quantized, works on CPU and GPU

### Diarization
- With diarization (`--diarize`) - Speaker identification enabled
- Without diarization - Transcription only

## Understanding Results

### RTF (Real-Time Factor)

RTF measures how fast the system processes audio compared to real-time:

```
RTF = Processing Time / Audio Duration
```

Examples:
- RTF = 0.05: Processes 1 minute of audio in 3 seconds (20x faster than real-time)
- RTF = 0.50: Processes 1 minute of audio in 30 seconds (2x faster than real-time)
- RTF = 1.00: Processes 1 minute of audio in 60 seconds (real-time)
- RTF = 2.00: Processes 1 minute of audio in 120 seconds (2x slower than real-time)

### WER (Word Error Rate)

WER measures transcription accuracy based on word-level errors:

```
WER = (Substitutions + Deletions + Insertions) / Total Words
```

Examples:
- WER = 0.00 (0%): Perfect transcription
- WER = 0.05 (5%): Excellent quality, 5 errors per 100 words
- WER = 0.10 (10%): Good quality, 10 errors per 100 words
- WER = 0.20 (20%): Acceptable for drafts, 20 errors per 100 words

## Example Workflow

### 1. Prepare Test Data

```bash
# Create test audio directory
mkdir -p benchmarks/test_audio

# Add your test audio files
cp /path/to/test/audio.wav benchmarks/test_audio/sample_1min.wav

# Edit ground truth
nano benchmarks/test_audio/ground_truth.json
```

### 2. Run Quick Test

```bash
cd benchmarks
./run_benchmarks.sh --quick
```

### 3. Review Results

```bash
# View summary
cat results/report.md

# Open in browser (if Markdown viewer available)
markdown results/report.md

# Analyze CSV data
python -c "import pandas as pd; print(pd.read_csv('results/report.csv'))"
```

### 4. Run Full Benchmark

```bash
./run_benchmarks.sh --full
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Benchmark Regression Test

on: [pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Quick Benchmark
        run: |
          cd benchmarks
          ./run_benchmarks.sh --quick
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: benchmarks/results/
```

## Troubleshooting

### Issue: "Test file not found"

**Solution**: Add audio files to `benchmarks/test_audio/`:
```bash
ls benchmarks/test_audio/
# Should show: sample_1min.wav, sample_5min.wav, etc.
```

### Issue: "WER calculation failed"

**Solution**: Ensure `ground_truth.json` has entries for your audio files:
```json
{
  "sample_1min.wav": "Your reference transcript here..."
}
```

### Issue: "CUDA out of memory"

**Solution**:
1. Use smaller models: `--models tiny,base,small`
2. Use CPU: `--devices cpu`
3. Test smaller audio files first

### Issue: "Benchmark script not executable"

**Solution** (Linux/Mac):
```bash
chmod +x benchmarks/run_benchmarks.sh
```

## Advanced Usage

### Custom Python Analysis

```python
import pandas as pd
import json
from pathlib import Path

# Load results
df = pd.read_csv('benchmarks/results/report.csv')

# Filter CUDA results
cuda_results = df[df['device'] == 'cuda']

# Find optimal configuration
optimal = df.loc[df['rtf'].idxmin()]
print(f"Fastest: {optimal['model']} with RTF={optimal['rtf']:.3f}")

most_accurate = df.loc[df['wer'].idxmin()]
print(f"Most accurate: {most_accurate['model']} with WER={most_accurate['wer']:.2%}")
```

### Generating Visualizations

```python
import matplotlib.pyplot as plt
import pandas as pd

df = pd.read_csv('benchmarks/results/report.csv')

# RTF vs WER scatter plot
plt.figure(figsize=(10, 6))
for model in df['model'].unique():
    model_data = df[df['model'] == model]
    plt.scatter(model_data['rtf'], model_data['wer'], label=model)

plt.xlabel('RTF (lower = faster)')
plt.ylabel('WER (lower = better)')
plt.title('TalkSmith: Speed vs Accuracy Trade-off')
plt.legend()
plt.grid(True)
plt.savefig('benchmarks/results/tradeoff.png')
```

## Metrics API

You can also use the metrics module directly in Python:

```python
from benchmarks.metrics import calculate_rtf, calculate_wer

# Calculate RTF
audio_duration = 300  # 5 minutes
process_time = 45     # 45 seconds
rtf = calculate_rtf(audio_duration, process_time)
print(f"RTF: {rtf:.3f}")  # 0.150

# Calculate WER
reference = "The quick brown fox jumps over the lazy dog"
hypothesis = "The quick brown fox jumped over the lazy dog"
wer = calculate_wer(reference, hypothesis)
print(f"WER: {wer:.2%}")  # 10.00%
```

## Best Practices

1. **Use Consistent Test Data**: Keep the same test audio files for comparing across versions
2. **Test Multiple Samples**: Use audio of different lengths (1min, 5min, 30min) to see scaling behavior
3. **Document GPU/CPU**: Record hardware specs with results for reproducibility
4. **Track Over Time**: Save results from each version to detect performance regressions
5. **Test Edge Cases**: Include challenging audio (accents, noise, multiple speakers)

## Future Enhancements

- Automated regression detection in CI
- Historical trend tracking and visualization
- Comparison with other transcription systems
- Language-specific benchmark suites
- Noise robustness testing
- Multi-GPU parallel benchmarking

## Support

For issues or questions:
- GitHub Issues: https://github.com/irsiksoftware/TalkSmith/issues
- Documentation: See `README.md` for general setup
