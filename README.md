# TalkSmith

> **Local, free, GPU-accelerated transcription and diarization pipeline for long-form multi-speaker audio**

⚠️ **Project Status: Early Development / Planning Phase**
This README documents the planned architecture and features. Implementation is in progress. See [Roadmap](#-roadmap) for current status.

---

TalkSmith is a comprehensive solution for transcribing and diarizing hour-long+ recordings with multiple speakers—completely free and running entirely on your local hardware. Built for professionals who need accurate, speaker-labeled transcripts without recurring cloud costs or privacy concerns.

## 🎯 What It Does

TalkSmith transforms your audio recordings into:
- **Accurate transcriptions** with word-level timestamps
- **Speaker diarization** (who said what and when)
- **Multiple export formats** (TXT, SRT, VTT, JSON)
- **Intelligent outlines** and summaries
- **Optional PRD/plan generation** from meeting transcripts

All powered by your local GPU(s), with support for multi-GPU parallelism to maximize throughput.

## 💰 Cost Savings

TalkSmith replaces expensive cloud transcription services with a one-time setup that pays for itself quickly:

| Service | Cost (per hour) | 100 Hours | 1000 Hours |
|---------|----------------|-----------|------------|
| **Rev.ai** | $1.25 | $125 | $1,250 |
| **Otter.ai Business** | $0.83* | $83 | $830 |
| **AssemblyAI** | $0.65 | $65 | $650 |
| **Deepgram** | $0.43 | $43 | $430 |
| **AWS Transcribe** | $0.024/min | $144 | $1,440 |
| **TalkSmith** | **$0** | **$0** | **$0** |

*Based on business plan pricing amortized per hour

### Products Replaced

- **Otter.ai** - Meeting transcription with speaker labels
- **Rev.ai** - Professional transcription service
- **Descript** - Audio/video transcription and editing
- **AssemblyAI** - API-based speech-to-text
- **Deepgram** - Real-time and batch transcription
- **Sonix** - Automated transcription with timestamps
- **Trint** - Transcription for media professionals
- **Happy Scribe** - Transcription and subtitling

**ROI Example:** If you transcribe 20 hours/month, you'd save $780-$1,500 annually compared to cloud services. With TalkSmith, your only costs are electricity (~$2-5/month for GPU usage).

## ✨ Key Features

### Core Capabilities
- 🚀 **GPU-accelerated** transcription with faster-whisper (CTranslate2)
- 👥 **Speaker diarization** via WhisperX + pyannote.audio
- 🎙️ **Multi-speaker support** for meetings, interviews, podcasts
- 📊 **Batch processing** with resume capability
- 🔧 **Audio preprocessing** (denoise, loudnorm, silence trimming)
- 📝 **Multiple export formats** (TXT, SRT, VTT, JSON)

### Advanced Features
- 💾 **Multi-GPU parallelism** (utilize multiple RTX 3060s concurrently)
- 🔄 **No-token diarization** alternative (no HuggingFace account required)
- 📋 **Speaker normalization** and outline generation
- 🔒 **PII scrubbing** for sensitive recordings
- ☁️ **Optional cloud sync** (rclone to Google Drive)
- 📄 **PRD/plan generation** from meeting transcripts

### Privacy & Control
- ✅ **100% local processing** - your audio never leaves your machine
- ✅ **No API keys or subscriptions** required (except optional HF token for best diarization)
- ✅ **Open source** - full transparency and customization
- ✅ **Offline capable** - no internet required after initial setup

## 🎮 Quick Start

> ⚠️ **Implementation in progress** - Installation and usage instructions below represent the planned interface. Check [Roadmap](#-roadmap) for current implementation status.

### Target Prerequisites
- **GPU:** NVIDIA GPU with CUDA support (tested on dual RTX 3060s, 12GB VRAM each)
- **OS:** Windows, Linux, or macOS (CPU-only mode on macOS)
- **Python:** 3.10 or 3.11
- **FFmpeg:** Required for audio processing

### Planned Installation

```bash
# 1. Clone the repository
git clone https://github.com/DakotaIrsik/TalkSmith.git
cd TalkSmith

# 2. Create environment (Windows PowerShell) - Coming soon
.\scripts\make_env.ps1

# 2. Create environment (Linux/macOS) - Coming soon
./scripts\make_env.sh

# 3. Verify GPU setup - Coming soon
python scripts/check_gpu.py

# 4. (Optional) Prefetch models - Coming soon
.\scripts\prefetch_models.ps1 --sizes medium.en,large-v3
```

### Planned Basic Usage

```bash
# Transcribe a single file
python pipeline/transcribe_fw.py path/to/audio.wav --model-size medium.en

# Transcribe with diarization
python pipeline/diarize_whisperx.py path/to/audio.wav

# Batch process a directory
.\scripts\batch_transcribe.ps1 --model-size large-v3 --diarization whisperx

# Generate outline from transcript
python pipeline/outline_from_segments.py path/to/segments.json
```

### Planned CLI Interface

```bash
# Unified CLI interface (in development)
python cli/main.py transcribe --input audio.wav --diarize --export srt,json
python cli/main.py batch --input-dir ./recordings --model large-v3
python cli/main.py plan --segments segments.json --output plan.md
```

## 🏗️ Architecture

> **Note:** This represents the planned directory structure. Implementation is in progress.

```
TalkSmith/
├── pipeline/           # Core processing modules
│   ├── transcribe_fw.py       # faster-whisper transcription
│   ├── diarize_whisperx.py    # WhisperX + pyannote diarization
│   ├── diarize_alt.py         # No-token alternative diarization
│   ├── preprocess.py          # Audio preprocessing
│   ├── postprocess_speakers.py # Speaker normalization
│   ├── outline_from_segments.py # Outline generation
│   └── logger.py              # ✅ Structured JSON logging
├── scripts/            # Automation and utilities
│   ├── batch_transcribe.ps1   # Batch processing (Windows)
│   ├── batch_transcribe.sh    # Batch processing (Linux)
│   ├── launcher.ps1/sh        # Multi-GPU job scheduler
│   └── check_gpu.py           # GPU verification
├── cli/                # Unified CLI interface
├── config/             # ✅ Configuration system
│   ├── settings.py            # Configuration loader
│   └── settings.ini           # Default settings
├── data/
│   ├── inputs/         # Place audio files here
│   ├── outputs/        # Transcripts and exports
│   └── samples/        # Test samples
├── docs/               # Documentation
├── benchmarks/         # Performance benchmarks
└── tests/              # ✅ Comprehensive test suite
```

## 🔧 Configuration

**✅ IMPLEMENTED** - Centralized configuration system with `settings.ini`

Configuration is managed through `config/settings.ini`:

```ini
[Paths]
input_dir = data/inputs
output_dir = data/outputs

[Models]
whisper_model = large-v3
diarization_model = pyannote/speaker-diarization-3.1

[Diarization]
mode = whisperx  # whisperx, alt, or off
vad_threshold = 0.5

[Export]
formats = txt,json,srt

[Logging]
level = INFO
format = json
log_dir = data/outputs/{slug}/logs
```

Override via environment variables (format: `TALKSMITH_<SECTION>_<KEY>`):
```bash
TALKSMITH_MODELS_WHISPER_MODEL=medium.en python pipeline/transcribe_fw.py audio.wav
```

See [docs/configuration.md](docs/configuration.md) for complete documentation.

## 📝 Logging

**✅ IMPLEMENTED** - Structured JSON logging with metrics tracking and retry/backoff

TalkSmith includes a comprehensive logging utility (`pipeline/logger.py`) that provides:
- **JSON-formatted logs** for easy parsing and analysis
- **Per-file log outputs** to `data/outputs/<slug>/logs/*.log`
- **Console and file output** with rotation support
- **Custom metrics tracking** for performance monitoring
- **Batch operation summaries** with success/failure tracking
- **Retry/backoff for transient errors** with exponential backoff

### Basic Logging

```python
from pipeline.logger import get_logger

# Create logger with slug for file-specific logging
logger = get_logger(__name__, slug='interview-2025-01-15')

# Log with custom fields
logger.info("Starting transcription", audio_file='test.wav')

# Log metrics
logger.log_metrics({
    'rtf': 0.12,
    'duration': 3600,
    'model': 'large-v3'
})

# Track batch operations
from pipeline.logger import BatchLogSummary
batch = BatchLogSummary(logger)
batch.record_success('file1.wav')
batch.record_failure('file2.wav', 'File not found')
batch.print_summary()
```

### Retry and Error Handling

```python
from pipeline.logger import get_logger, with_retry, retry_operation, TransientError

logger = get_logger(__name__)

# Using decorator for retry with exponential backoff
@with_retry(max_attempts=3, initial_delay=1.0, backoff_factor=2.0, logger=logger)
def fetch_model():
    # Code that may fail transiently (network issues, API limits, etc.)
    return download_model()

# Using functional approach
result = retry_operation(
    lambda: api_call(),
    max_attempts=5,
    logger=logger,
    operation_name='api_fetch'
)
```

## 📊 Performance

> **Note:** These are target performance metrics based on preliminary testing. Full benchmarks will be published after implementation.

Target benchmarks on dual RTX 3060 setup (12GB VRAM each):

| Audio Length | Model | Single GPU RTF* | Dual GPU RTF* | Speedup |
|--------------|-------|----------------|---------------|---------|
| 60 min | medium.en | 0.12 | 0.06 | 2.0x |
| 60 min | large-v3 | 0.21 | 0.11 | 1.9x |
| 120 min | large-v3 | 0.21 | 0.11 | 1.9x |

*RTF = Real-Time Factor (lower is faster). RTF of 0.12 means 60 minutes processes in ~7 minutes.

## 🎯 Use Cases

- **Product Managers:** Transcribe customer interviews and generate PRDs
- **Researchers:** Analyze interview data with speaker attribution
- **Content Creators:** Subtitle podcasts and videos
- **Journalists:** Transcribe interviews and press conferences
- **Students:** Transcribe lectures with speaker identification
- **Legal/Medical:** Transcribe depositions/consultations (with PII scrubbing)

## 🛣️ Roadmap

See our [GitHub Issues](https://github.com/DakotaIrsik/TalkSmith/issues) for detailed planning:

**Phase 1: Foundation (P0)** - *In Progress*
- [x] Repository structure and documentation
- [x] Centralized configuration system (settings.ini)
- [x] Comprehensive test suite and CI/CD pipeline
- [x] Structured JSON logging utility
- [ ] GPU and CUDA verification
- [ ] Python environment setup
- [ ] Core transcription pipeline (faster-whisper)
- [ ] Diarization (WhisperX + pyannote)
- [ ] Batch processing with resume
- [ ] Export formats

**Phase 2: Enhancement (P1)**
- [ ] Audio preprocessing (denoise, trim)
- [ ] Multi-GPU parallelism
- [ ] Speaker post-processing and outlines
- [ ] CLI wrapper

**Phase 3: Advanced (P2)**
- [ ] Alternative diarization (no HF token)
- [ ] Benchmark suite
- [ ] Google Drive sync
- [ ] Plan/PRD generation
- [ ] Docker (CUDA) support
- [ ] PII scrubbing

## 🧪 Testing

**✅ IMPLEMENTED** - Comprehensive test suite with CI/CD automation

```bash
# Run all tests
make test

# Run with coverage report
make coverage

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
```

See [TESTING.md](TESTING.md) for detailed testing documentation and [tests/README.md](tests/README.md) for quick reference.

## 🤝 Contributing

We welcome contributions! Contribution guidelines coming soon.

Before submitting a PR:
- ✅ Run tests: `make test`
- ✅ Check coverage: `make coverage`
- ✅ Review [TESTING.md](TESTING.md) for testing standards

## 📄 License

License TBD - Will be added in a future release.

## 🙏 Acknowledgments

Built on the shoulders of giants:
- **faster-whisper** by Guillaume Klein (CTranslate2-optimized Whisper)
- **WhisperX** by Max Bain (alignment and diarization)
- **pyannote.audio** by Hervé Bredin (speaker diarization)
- **OpenAI Whisper** (original ASR model)

## 📞 Support

- 🐛 **Issues:** [GitHub Issues](https://github.com/DakotaIrsik/TalkSmith/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/DakotaIrsik/TalkSmith/discussions)
- 📖 **Docs:** [docs/](docs/)

---

**Made with ❤️ for developers who value privacy, control, and zero recurring costs.**
