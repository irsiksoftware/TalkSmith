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

### Core Capabilities (Planned)
- 🚀 **GPU-accelerated** transcription with faster-whisper (CTranslate2)
- 👥 **Speaker diarization** via WhisperX + pyannote.audio OR token-free alternative
- 🎙️ **Multi-speaker support** for meetings, interviews, podcasts
- 📊 **Batch processing** with resume capability
- 🔧 **Audio preprocessing** (denoise, loudnorm, silence trimming)
- 📝 **Multiple export formats** (TXT, SRT, VTT, JSON) - ✅ Implemented

### Implemented Features
- ✅ **Structured JSON logging** with metrics tracking and retry/backoff
- ✅ **Export formats** - TXT, SRT, VTT, JSON with validation
- ✅ **CLI interface** - Export and batch processing commands
- ✅ **PII redaction** - Emails, phones, SSNs, credit cards, IPs
- ✅ **Model cache management** - Prefetch models for offline use
- ✅ **Configuration system** - Centralized settings.ini with env overrides
- ✅ **Comprehensive testing** - Unit, integration, and CI/CD automation
- ✅ **Speaker post-processing** - Normalize speaker labels and merge utterances
- ✅ **Outline generation** - Timestamped outlines with auto topic detection
- ✅ **WhisperX diarization** - GPU-accelerated diarization with pyannote.audio

### Advanced Features (Planned)
- 💾 **Multi-GPU parallelism** (utilize multiple RTX 3060s concurrently)
- ✅ **No-token diarization** alternative (no HuggingFace account required) - ✅ Implemented
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

**Option 1: Docker (Recommended for Linux/GPU)** - ✅ IMPLEMENTED

```bash
# 1. Clone the repository
git clone https://github.com/DakotaIrsik/TalkSmith.git
cd TalkSmith

# 2. Ensure nvidia-docker2 or nvidia-container-toolkit is installed
# See: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

# 3. Build and run with Docker Compose
docker compose up -d

# 4. Run transcription (example)
docker compose run talksmith python cli/main.py export --help

# 5. Stop container
docker compose down
```

See [Docker Setup](#-docker-setup-cuda) for detailed instructions.

**Option 2: Native Installation**

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

# 4. (Optional) Prefetch models - ✅ IMPLEMENTED
.\scripts\prefetch_models.ps1 -Sizes "medium.en,large-v3"
```

### Planned Basic Usage

```bash
# Transcribe a single file (not yet implemented)
python pipeline/transcribe_fw.py path/to/audio.wav --model-size medium.en

# Transcribe with diarization - WhisperX - ✅ IMPLEMENTED
python pipeline/diarize_whisperx.py path/to/audio.wav --hf-token YOUR_HF_TOKEN

# Transcribe with token-free diarization - ✅ IMPLEMENTED
python pipeline/diarize_alt.py path/to/audio.wav -o segments.json

# Batch process a directory (not yet implemented)
.\scripts\batch_transcribe.ps1 --model-size large-v3 --diarization whisperx

# Post-process speaker labels - ✅ IMPLEMENTED
python pipeline/postprocess_speakers.py segments.json --min-utterance-ms 1000

# Generate outline from transcript - ✅ IMPLEMENTED
python pipeline/outline_from_segments.py segments.json --interval 60
```

### CLI Interface

**✅ IMPLEMENTED** - Unified CLI with export and batch processing

```bash
# Export segments to various formats
python cli/main.py export --input segments.json --formats txt,srt,vtt,json --output-dir ./output

# Batch export multiple files
python cli/main.py batch --input-dir ./segments --formats srt,json --output-dir ./transcripts

# Demonstrate logging and error handling
python cli/main.py demo
```

**Planned subcommands** (coming soon):
```bash
python cli/main.py transcribe --input audio.wav --diarize --export srt,json
python cli/main.py preprocess --input audio.wav --denoise --trim
python cli/main.py plan --segments segments.json --output plan.md
```

## 🏗️ Architecture

> **Note:** This represents the planned directory structure. Implementation is in progress.

```
TalkSmith/
├── pipeline/           # Core processing modules
│   ├── transcribe_fw.py       # faster-whisper transcription (planned)
│   ├── diarize_whisperx.py    # ✅ WhisperX + pyannote diarization
│   ├── diarize_alt.py         # ✅ No-token alternative diarization
│   ├── preprocess.py          # Audio preprocessing (planned)
│   ├── postprocess_speakers.py # ✅ Speaker normalization and utterance merging
│   ├── outline_from_segments.py # ✅ Outline generation with topic detection
│   ├── exporters.py           # ✅ Export formats (TXT, SRT, VTT, JSON)
│   ├── redact_pii.py          # ✅ PII redaction
│   └── logger.py              # ✅ Structured JSON logging
├── scripts/            # Automation and utilities
│   ├── batch_transcribe.ps1   # Batch processing (planned)
│   ├── batch_transcribe.sh    # Batch processing (planned)
│   ├── launcher.ps1/sh        # Multi-GPU job scheduler (planned)
│   ├── prefetch_models.ps1    # ✅ Model cache management (Windows)
│   ├── prefetch_models.sh     # ✅ Model cache management (Linux/macOS)
│   ├── make_env.ps1           # Environment setup (Windows)
│   └── check_gpu.py           # GPU verification (planned)
├── cli/                # ✅ Unified CLI interface
│   └── main.py                # CLI with export, batch, demo commands
├── config/             # ✅ Configuration system
│   ├── settings.py            # Configuration loader
│   └── settings.ini           # Default settings
├── data/
│   ├── inputs/         # Place audio files here
│   ├── outputs/        # Transcripts and exports
│   └── samples/        # ✅ Test samples
├── docs/               # ✅ Documentation
│   ├── configuration.md       # Configuration guide
│   ├── diarization.md         # ✅ Diarization comparison guide
│   └── consent_template.md    # Recording consent template
├── benchmarks/         # Performance benchmarks (planned)
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

## 🎤 Speaker Post-Processing

**✅ IMPLEMENTED** - Normalize speaker labels and merge short utterances

The `postprocess_speakers.py` module improves transcript readability by normalizing speaker labels and merging fragmented utterances.

### Features

- **Speaker normalization** - Convert diarization labels (SPEAKER_00, SPEAKER_01) to human-readable format (Speaker 1, Speaker 2)
- **Utterance merging** - Merge short utterances from the same speaker to reduce fragmentation
- **Configurable thresholds** - Control minimum utterance duration and speaker prefix

### Usage

```python
from pipeline.postprocess_speakers import postprocess_speakers

# Normalize speaker labels and merge short utterances
processed = postprocess_speakers(
    segments,
    normalize_names=True,
    speaker_prefix="Speaker",
    min_utterance_ms=1000  # Merge utterances shorter than 1 second
)
```

### CLI Usage

```bash
# Basic usage with default settings
python pipeline/postprocess_speakers.py segments.json

# Custom output file
python pipeline/postprocess_speakers.py segments.json -o processed.json

# Custom speaker prefix
python pipeline/postprocess_speakers.py segments.json --speaker-prefix "Person"

# Adjust minimum utterance duration (milliseconds)
python pipeline/postprocess_speakers.py segments.json --min-utterance-ms 2000

# Disable speaker normalization
python pipeline/postprocess_speakers.py segments.json --no-normalize-names
```

## 📋 Outline Generation

**✅ IMPLEMENTED** - Generate timestamped outlines from transcripts

The `outline_from_segments.py` module creates navigable outlines with timestamp anchors for easy reference.

### Features

- **Timestamped entries** - [HH:MM:SS] anchors for quick navigation
- **Auto topic detection** - Identifies topic changes based on speaker switches and silence gaps
- **Configurable intervals** - Control outline granularity with time intervals
- **Markdown output** - Clean, readable format for easy sharing

### Usage

```python
from pipeline.outline_from_segments import generate_outline, format_outline_markdown

# Generate outline with auto topic detection
outline_entries = generate_outline(
    segments,
    interval_seconds=60.0,  # Entry every 60 seconds
    auto_detect_topics=True,
    gap_threshold=3.0  # 3 seconds silence = topic change
)

# Format as Markdown
markdown = format_outline_markdown(outline_entries, title="Meeting Outline")
```

### CLI Usage

```bash
# Basic usage - generates outline with 60-second intervals
python pipeline/outline_from_segments.py segments.json

# Custom output file and title
python pipeline/outline_from_segments.py segments.json -o outline.md --title "Q4 Planning"

# Adjust time interval (seconds)
python pipeline/outline_from_segments.py segments.json --interval 120

# Disable time interval (topic detection only)
python pipeline/outline_from_segments.py segments.json --interval 0

# Adjust silence gap threshold for topic detection
python pipeline/outline_from_segments.py segments.json --gap-threshold 5.0

# Disable auto topic detection
python pipeline/outline_from_segments.py segments.json --no-auto-detect
```

### Example Output

```markdown
# Transcript Outline

## [00:00:00] Speaker 1
Introduction and welcome to the meeting. Discussing today's agenda and...

## [00:01:30] Speaker 2
Updates on the project timeline. We've made significant progress on...

## [00:03:45] Speaker 1
Questions about the budget. How are we tracking against our...
```

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

## 🗂️ Model Cache Management

**✅ IMPLEMENTED** - Prefetch and cache models for offline use

TalkSmith includes utilities to prefetch Whisper and diarization models, enabling fully offline transcription and reducing first-run latency.

### Prefetch Models

**Windows (PowerShell):**
```powershell
# Download default models (medium.en, large-v3)
.\scripts\prefetch_models.ps1

# Download specific models
.\scripts\prefetch_models.ps1 -Sizes "small.en,medium.en,large-v3"

# Skip diarization models (no HF token required)
.\scripts\prefetch_models.ps1 -SkipDiarization

# With HuggingFace token for diarization
.\scripts\prefetch_models.ps1 -HfToken "hf_xxxxx"

# Custom cache directory
.\scripts\prefetch_models.ps1 -CacheDir "D:\Models"
```

**Linux/macOS (Bash):**
```bash
# Download default models
./scripts/prefetch_models.sh

# Download specific models
./scripts/prefetch_models.sh --sizes "small.en,medium.en,large-v3"

# Skip diarization models
./scripts/prefetch_models.sh --skip-diarization

# With HuggingFace token
./scripts/prefetch_models.sh --hf-token "hf_xxxxx"

# Custom cache directory
./scripts/prefetch_models.sh --cache-dir "/mnt/models"
```

### Available Whisper Models

| Model | Parameters | Disk Size | VRAM (FP16) | Use Case |
|-------|-----------|-----------|-------------|----------|
| `tiny.en` | 39M | ~75 MB | ~1 GB | Testing, very fast |
| `base.en` | 74M | ~150 MB | ~1 GB | Lightweight |
| `small.en` | 244M | ~500 MB | ~2 GB | Good accuracy, faster |
| `medium.en` | 769M | ~1.5 GB | ~5 GB | **Recommended for English** |
| `large-v3` | 1550M | ~3 GB | ~10 GB | **Best accuracy** |

*Non-`.en` models also available for multi-language support*

### Model Selection Guidelines

- **English-only content:** Use `.en` models (faster, more accurate)
- **Production/critical work:** `large-v3` or `medium.en`
- **Rapid iteration/testing:** `small.en` or `base.en`
- **Multi-language:** Use non-`.en` variants

### Cache Configuration

Models are cached in `.cache/` by default (configurable in `config/settings.ini`):

```ini
[Paths]
cache_dir = .cache

[Models]
whisper_model = large-v3
diarization_model = pyannote/speaker-diarization-3.1
```

See [DECISIONS.md](DECISIONS.md) for detailed model selection rationale and version pinning strategy.

## 🔒 PII Redaction

**✅ IMPLEMENTED** - Comprehensive PII redaction for sensitive recordings

TalkSmith includes built-in PII (Personally Identifiable Information) redaction to protect sensitive data in transcripts:

### Redaction Features

- **Email addresses** - Redacts email patterns
- **Phone numbers** - US and international formats
- **Social Security Numbers** - SSN patterns
- **Credit card numbers** - Major card types (Visa, MasterCard, etc.)
- **IP addresses** - IPv4 and IPv6
- **Whitelist support** - Exclude known safe patterns from redaction

### Basic Usage

```python
from pipeline.redact_pii import redact_pii

# Redact PII from transcript segments
redacted = redact_pii(
    segments,
    redact_emails=True,
    redact_phones=True,
    redact_ssns=True,
    redact_credit_cards=True,
    redact_ips=True
)

# Use whitelist to preserve known safe values
safe_patterns = [
    r'support@mycompany\.com',
    r'555-0100'  # Demo phone number
]
redacted = redact_pii(segments, whitelist=safe_patterns)
```

### Recording Consent

Before recording sensitive conversations, use our consent template:

```bash
# View consent template
cat docs/consent_template.md
```

The template includes legally-compliant consent language and PII handling procedures. See [docs/consent_template.md](docs/consent_template.md) for details.

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
- [x] Export formats (TXT, SRT, VTT, JSON)
- [x] CLI wrapper (export, batch commands)
- [x] Diarization (WhisperX + pyannote)
- [ ] GPU and CUDA verification
- [ ] Python environment setup
- [ ] Core transcription pipeline (faster-whisper)
- [ ] Batch processing with resume

**Phase 2: Enhancement (P1)**
- [ ] Audio preprocessing (denoise, trim)
- [ ] Multi-GPU parallelism
- [x] Speaker post-processing (normalization, utterance merging)
- [x] Outline generation with topic detection
- [ ] Additional CLI subcommands (transcribe, preprocess, etc.)

**Phase 3: Advanced (P2)**
- [x] Model cache management and version pinning
- [x] PII redaction with whitelist support
- [x] Docker (CUDA) support
- [x] Alternative diarization (no HF token)
- [ ] Benchmark suite
- [ ] Google Drive sync
- [ ] Plan/PRD generation

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
