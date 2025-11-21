# Audio Preprocessing Guide

TalkSmith includes a comprehensive audio preprocessing pipeline that can significantly improve transcription quality by cleaning and normalizing audio before it reaches the Whisper model.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Preprocessing Steps](#preprocessing-steps)
- [Integration with Transcription](#integration-with-transcription)
- [Configuration](#configuration)
- [CLI Usage](#cli-usage)
- [API Usage](#api-usage)
- [Performance Considerations](#performance-considerations)
- [Troubleshooting](#troubleshooting)

## Overview

Audio preprocessing improves transcription accuracy by:
- **Removing background noise** - Eliminates static, hum, and ambient noise
- **Normalizing loudness** - Ensures consistent audio levels for better recognition
- **Trimming silence** - Removes dead air from beginning/end to reduce processing time
- **Filtering low frequencies** - Removes rumble and bass noise below speech range

The preprocessing pipeline is **optional** and can be enabled/disabled per transcription job or globally via configuration.

## Installation

All required preprocessing dependencies are included in the main requirements:

```bash
pip install -r requirements.txt
```

### Key Dependencies

- **soundfile** (≥0.12.1) - Audio file I/O
- **scipy** (≥1.11.0) - Signal processing for filters
- **librosa** (≥0.10.0) - Audio analysis
- **noisereduce** (≥3.0.0) - Advanced noise reduction

If you're using a minimal installation, ensure these are installed:

```bash
pip install soundfile scipy librosa noisereduce
```

## Quick Start

### Using the Transcription CLI with Preprocessing

Transcribe with preprocessing enabled:

```bash
python pipeline/transcribe_fw.py input.wav \
    --preprocess \
    --denoise \
    --loudnorm \
    --trim-silence
```

### Batch Transcription with Preprocessing

Process multiple files with preprocessing:

```bash
python scripts/batch_transcribe.py data/inputs \
    --output-dir data/outputs \
    --preprocess \
    --denoise \
    --loudnorm
```

### Standalone Preprocessing

Preprocess audio without transcription:

```bash
python pipeline/preprocess.py input.wav \
    --denoise \
    --loudnorm \
    --trim-silence \
    --high-pass-filter \
    -o preprocessed.wav
```

## Preprocessing Steps

### 1. High-Pass Filter

Removes low-frequency noise (rumble, hum, HVAC noise).

**Parameters:**
- `--high-pass-filter` - Enable the filter
- `--hpf-cutoff <Hz>` - Cutoff frequency (default: 80 Hz)

**When to use:**
- Audio recorded in noisy environments
- Recordings with AC hum or rumble
- Podcasts with low-frequency background noise

**Example:**
```bash
--high-pass-filter --hpf-cutoff 100
```

### 2. Denoising

Removes background noise using spectral gating or deep learning.

**Parameters:**
- `--denoise` - Enable denoising
- `--denoise-method <method>` - Method: `noisereduce` (default) or `ffmpeg`

**Methods:**
- **noisereduce** - Spectral gating with automatic noise profile detection
- **ffmpeg** - Requires external processing (placeholder in current implementation)

**When to use:**
- Recordings with constant background noise
- Static or white noise in audio
- Outdoor recordings with ambient noise

**Example:**
```bash
--denoise --denoise-method noisereduce
```

**Note:** The noisereduce method uses stationary noise reduction with 80% noise reduction strength.

### 3. Loudness Normalization

Normalizes audio volume to a consistent target level (EBU R128 standard, -3 dBFS).

**Parameters:**
- `--loudnorm` - Enable loudness normalization

**When to use:**
- Quiet or inconsistent audio levels
- Multiple speakers with varying volumes
- Audio from different sources

**Example:**
```bash
--loudnorm
```

**Technical Details:**
- Target peak level: -3 dBFS
- Uses simple peak normalization
- Preserves dynamic range

### 4. Silence Trimming

Removes silence from the beginning and end of audio.

**Parameters:**
- `--trim-silence` - Enable silence trimming
- `--silence-threshold <dB>` - Threshold in dB (default: -40 dB)

**When to use:**
- Recordings with long pauses at start/end
- Reducing processing time for batch jobs
- Cleaning up recorded meetings/calls

**Example:**
```bash
--trim-silence --silence-threshold -35
```

**Technical Details:**
- Detects silence using power-based threshold
- Minimum duration: 0.3 seconds (configurable)
- Preserves 0.15s buffer on each side

## Integration with Transcription

### Automatic Integration

Preprocessing is automatically integrated into the transcription pipeline when enabled:

```
Audio Input
    ↓
[Preprocessing Pipeline] ← (optional, enabled via --preprocess)
    ├─ High-Pass Filter
    ├─ Denoising
    ├─ Silence Trimming
    └─ Loudness Normalization
    ↓
[Temporary Preprocessed File]
    ↓
[Faster-Whisper Transcription]
    ↓
[Cleanup Temp Files]
    ↓
Transcription Output (with preprocessing metrics)
```

### Preprocessing Metrics

When preprocessing is enabled, the transcription result includes detailed metrics:

```json
{
  "text": "Transcribed text...",
  "segments": [...],
  "preprocessing": {
    "input_file": "/path/to/original.wav",
    "output_file": "/tmp/preprocessed_xyz.wav",
    "steps_applied": [
      "high_pass_filter",
      "denoise_noisereduce",
      "trim_silence",
      "loudness_normalization"
    ],
    "original_duration_seconds": 120.5,
    "final_duration_seconds": 118.2,
    "duration_change_seconds": 2.3,
    "silence_trimmed_seconds": 2.3,
    "sample_rate": 16000
  }
}
```

### Error Handling

The preprocessing pipeline includes graceful error handling:
- If preprocessing fails, the original audio is used
- Warnings are logged but transcription continues
- Missing optional dependencies are handled gracefully

## Configuration

### Configuration File (`config/settings.ini`)

Set default preprocessing options in the configuration file:

```ini
[Processing]
# Enable preprocessing pipeline before transcription
enable_preprocessing = false

# Denoising: Remove background noise from audio
denoise = false
denoise_method = noisereduce  # Options: noisereduce, ffmpeg

# Loudness normalization: Normalize audio volume (EBU R128 standard, -3 dBFS target)
normalize_audio = true

# Silence trimming: Remove silence from beginning and end of audio
trim_silence = false
silence_threshold_db = -40.0  # Silence threshold in dB
min_silence_duration = 0.3    # Minimum silence duration to trim (seconds)

# High-pass filter: Remove low-frequency noise (rumble, hum)
high_pass_filter = false
hpf_cutoff = 80  # High-pass filter cutoff frequency in Hz

# Target sample rate in Hz
sample_rate = 16000
```

### Environment Variables

Override configuration via environment variables:

```bash
export TALKSMITH_PROCESSING_ENABLE_PREPROCESSING=true
export TALKSMITH_PROCESSING_DENOISE=true
export TALKSMITH_PROCESSING_NORMALIZE_AUDIO=true
```

## CLI Usage

### Transcription with Preprocessing

Single file transcription:

```bash
python pipeline/transcribe_fw.py audio.wav \
    --model-size medium \
    --device cuda \
    --preprocess \
    --denoise \
    --loudnorm \
    --trim-silence \
    --high-pass-filter
```

### Batch Transcription with Preprocessing

Process directory of audio files:

```bash
python scripts/batch_transcribe.py data/inputs \
    --output-dir data/outputs \
    --model medium.en \
    --preprocess \
    --denoise \
    --loudnorm \
    --formats txt json srt
```

### Standalone Preprocessing

Preprocess only (no transcription):

```bash
python pipeline/preprocess.py input.wav \
    -o output.wav \
    --denoise \
    --denoise-method noisereduce \
    --loudnorm \
    --trim-silence \
    --silence-threshold -35 \
    --high-pass-filter \
    --hpf-cutoff 100
```

## API Usage

### Using AudioPreprocessor Directly

```python
from pathlib import Path
from pipeline.preprocess import AudioPreprocessor

# Initialize preprocessor
preprocessor = AudioPreprocessor(
    denoise=True,
    denoise_method="noisereduce",
    loudnorm=True,
    trim_silence=True,
    silence_threshold_db=-40.0,
    high_pass_filter=True,
    hpf_cutoff=80
)

# Process audio
input_path = Path("input.wav")
output_path = Path("preprocessed.wav")
output_path, metrics = preprocessor.process(input_path, output_path)

print(f"Preprocessing complete: {metrics['steps_applied']}")
print(f"Duration change: {metrics['duration_change_seconds']:.2f}s")
```

### Using FasterWhisperTranscriber with Preprocessing

```python
from pipeline.transcribe_fw import FasterWhisperTranscriber

# Initialize transcriber with preprocessing
transcriber = FasterWhisperTranscriber(
    model_size="medium",
    device="cuda",
    enable_preprocessing=True,
    denoise=True,
    loudnorm=True,
    trim_silence=True,
    high_pass_filter=True
)

# Transcribe with automatic preprocessing
result = transcriber.transcribe("audio.wav")

# Access preprocessing metrics
if "preprocessing" in result:
    print(f"Preprocessing steps: {result['preprocessing']['steps_applied']}")
    print(f"Original duration: {result['preprocessing']['original_duration_seconds']:.2f}s")
    print(f"Final duration: {result['preprocessing']['final_duration_seconds']:.2f}s")

print(f"Transcription: {result['text']}")
```

### Using BatchTranscriber with Preprocessing

```python
from pathlib import Path
from scripts.batch_transcribe import BatchTranscriber

# Initialize batch transcriber with preprocessing
batch_transcriber = BatchTranscriber(
    input_dir=Path("data/inputs"),
    output_dir=Path("data/outputs"),
    model_size="medium",
    device="cuda",
    enable_preprocessing=True,
    denoise=True,
    loudnorm=True,
    trim_silence=True,
    high_pass_filter=False,
    formats=["txt", "json", "srt"]
)

# Process all files
exit_code = batch_transcriber.run()
```

## Performance Considerations

### Processing Time

Preprocessing adds overhead to transcription:

- **High-pass filter**: +5-10% processing time
- **Denoising**: +20-30% processing time (depends on audio length)
- **Loudness normalization**: +2-5% processing time
- **Silence trimming**: Negligible to negative (reduces transcription time)

**Example timings** (2-minute audio file):
- Without preprocessing: ~15 seconds
- With all preprocessing: ~20 seconds
- **Net benefit**: Improved accuracy often worth the extra time

### Memory Usage

Preprocessing loads entire audio file into memory:
- **Typical usage**: 10-50 MB per minute of audio (16 kHz mono)
- **Peak usage**: 2x audio size during processing
- **Recommendation**: 1 GB RAM minimum for preprocessing

### Disk Space

Temporary preprocessed files are created during transcription:
- **Location**: System temp directory (usually `/tmp`)
- **Size**: Same as input audio (WAV format)
- **Cleanup**: Automatic after transcription
- **Recommendation**: 500 MB free temp space per concurrent job

### Parallel Processing

When using batch processing with `--parallel`:
- Each worker creates its own preprocessor
- Memory usage scales with `--workers` count
- **Recommendation**: 2-4 workers for systems with 8+ GB RAM

## Troubleshooting

### Common Issues

#### 1. Missing Dependencies

**Error:**
```
ImportError: No module named 'noisereduce'
```

**Solution:**
```bash
pip install noisereduce
```

#### 2. Scipy Not Available for High-Pass Filter

**Warning:**
```
scipy not available, skipping high-pass filter
```

**Solution:**
```bash
pip install scipy
```

#### 3. Noisereduce Not Available

**Warning:**
```
noisereduce not available, falling back to ffmpeg denoising
```

**Solution:**
Install noisereduce or disable denoising:
```bash
pip install noisereduce
# OR
--denoise false
```

#### 4. Audio Quality Degradation

If preprocessed audio sounds worse:

1. **Disable aggressive denoising:**
   ```bash
   --denoise false
   ```

2. **Reduce silence threshold:**
   ```bash
   --silence-threshold -50
   ```

3. **Disable high-pass filter for low-pitched voices:**
   ```bash
   --high-pass-filter false
   ```

4. **Use only loudness normalization:**
   ```bash
   --preprocess --loudnorm
   ```

#### 5. Preprocessing Takes Too Long

For faster processing:

1. **Disable denoising** (slowest step):
   ```bash
   --preprocess --loudnorm --trim-silence
   ```

2. **Use only silence trimming** (can reduce transcription time):
   ```bash
   --preprocess --trim-silence
   ```

3. **Process smaller batches:**
   ```bash
   --workers 1
   ```

### Best Practices

#### When to Use Preprocessing

✅ **Recommended for:**
- Noisy recordings (background noise, static)
- Quiet or inconsistent audio levels
- Multiple speakers with varying volumes
- Phone calls or VoIP recordings
- Outdoor recordings
- Podcast audio

❌ **Not necessary for:**
- Studio-quality recordings
- Already clean audio
- Time-critical processing
- Very short clips (<5 seconds)

#### Recommended Presets

**Podcast/Interview:**
```bash
--preprocess --denoise --loudnorm
```

**Phone Call/VoIP:**
```bash
--preprocess --denoise --loudnorm --high-pass-filter --hpf-cutoff 100
```

**Conference Room Recording:**
```bash
--preprocess --denoise --loudnorm --trim-silence
```

**High-Quality Studio:**
```bash
# No preprocessing needed, or just:
--preprocess --loudnorm
```

### Performance Tuning

#### For Maximum Accuracy
```bash
--preprocess \
--denoise --denoise-method noisereduce \
--loudnorm \
--trim-silence --silence-threshold -35 \
--high-pass-filter --hpf-cutoff 80
```

#### For Maximum Speed
```bash
--preprocess --trim-silence
# OR just skip preprocessing entirely
```

#### Balanced (Recommended)
```bash
--preprocess --denoise --loudnorm
```

## Advanced Topics

### Custom Preprocessing Pipeline

Create custom preprocessing workflows:

```python
from pipeline.preprocess import AudioPreprocessor
import soundfile as sf
import numpy as np

# Custom preprocessing with additional steps
preprocessor = AudioPreprocessor(
    denoise=True,
    loudnorm=True,
    trim_silence=True,
    high_pass_filter=True
)

# Load audio
audio, sr = sf.read("input.wav")

# Your custom processing here
# e.g., apply custom EQ, compression, etc.

# Save to temporary file
temp_path = "temp.wav"
sf.write(temp_path, audio, sr)

# Apply standard preprocessing
output_path, metrics = preprocessor.process(temp_path)
```

### Batch Configuration

Process different file types with different settings:

```python
from pathlib import Path
from pipeline.transcribe_fw import FasterWhisperTranscriber

configs = {
    "podcast": {"denoise": True, "loudnorm": True, "trim_silence": False},
    "calls": {"denoise": True, "loudnorm": True, "high_pass_filter": True},
    "studio": {"denoise": False, "loudnorm": True, "trim_silence": False}
}

for audio_file in Path("data/inputs").glob("*.wav"):
    # Determine config based on filename or metadata
    config_name = "podcast"  # Your logic here
    config = configs[config_name]

    transcriber = FasterWhisperTranscriber(
        model_size="medium",
        device="cuda",
        enable_preprocessing=True,
        **config
    )

    result = transcriber.transcribe(str(audio_file))
```

## Related Documentation

- [Transcription Guide](TRANSCRIPTION.md)
- [Batch Processing Guide](BATCH_PROCESSING.md)
- [API Reference](API.md)
- [Configuration Guide](CONFIGURATION.md)

## Support

For issues, questions, or contributions:
- GitHub Issues: [TalkSmith Issues](https://github.com/irsiksoftware/TalkSmith/issues)
- Documentation: [TalkSmith Docs](https://github.com/irsiksoftware/TalkSmith/tree/main/docs)
