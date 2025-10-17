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
- **PRD/plan generation** from meeting transcripts with Google Docs integration

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
- ✅ **Plan/PRD generation** - LLM-powered structured plans from transcripts with Google Docs publishing
- ✅ **WhisperX diarization** - GPU-accelerated diarization with pyannote.audio

### Advanced Features (Planned)
- 💾 **Multi-GPU parallelism** (utilize multiple RTX 3060s concurrently)
- ✅ **No-token diarization** alternative (no HuggingFace account required) - ✅ Implemented
- ☁️ **Optional cloud sync** (rclone to Google Drive) - ✅ Implemented

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

## 🚀 Installation

### Prerequisites

Before installing TalkSmith, ensure you have:

- **Python:** Version 3.10 or 3.11
- **GPU (Recommended):** NVIDIA GPU with CUDA support (e.g., RTX 3060, 12GB+ VRAM)
  - For CPU-only installation, use the `cpu` option in setup scripts
- **FFmpeg:** Required for audio processing
  - **Windows:** `choco install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
  - **Linux:** `sudo apt install ffmpeg` (Ubuntu/Debian) or equivalent
  - **macOS:** `brew install ffmpeg`
- **Git:** For cloning the repository

### Installation Methods

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

**Option 2: Native Installation** - ✅ IMPLEMENTED

#### Windows (PowerShell)

```powershell
# 1. Clone the repository
git clone https://github.com/DakotaIrsik/TalkSmith.git
cd TalkSmith

# 2. Run environment setup script
.\scripts\make_env.ps1

# For CPU-only installation:
.\scripts\make_env.ps1 -CudaVersion cpu

# For conda environment (requires Anaconda/Miniconda):
.\scripts\make_env.ps1 -EnvType conda

# 3. Activate the environment
.\venv\Scripts\Activate.ps1
# OR for conda: conda activate talksmith

# 4. Verify installation
python scripts\check_gpu.py
python scripts\check_ffmpeg.py

# 5. (Optional) Prefetch models for offline use
.\scripts\prefetch_models.ps1 -Sizes "medium.en,large-v3"
```

#### Linux/macOS (Bash)

```bash
# 1. Clone the repository
git clone https://github.com/DakotaIrsik/TalkSmith.git
cd TalkSmith

# 2. Make scripts executable and run setup
chmod +x scripts/make_env.sh
./scripts/make_env.sh

# For CPU-only installation:
./scripts/make_env.sh venv 3.11 cpu

# For conda environment (requires Anaconda/Miniconda):
./scripts/make_env.sh conda

# 3. Activate the environment
source venv/bin/activate
# OR for conda: conda activate talksmith

# 4. Verify installation
python scripts/check_gpu.py
python scripts/check_ffmpeg.py

# 5. (Optional) Prefetch models for offline use
./scripts/prefetch_models.sh --sizes "medium.en,large-v3"
```

### What the Setup Script Does

The `make_env.ps1` (Windows) and `make_env.sh` (Linux/macOS) scripts automate the following:

1. **Environment Creation:** Creates a Python virtual environment or Conda environment
2. **Dependency Installation:** Installs PyTorch with CUDA support and all TalkSmith dependencies
3. **FFmpeg Verification:** Checks that FFmpeg is installed and accessible
4. **CUDA Verification:** Tests GPU availability through PyTorch
5. **Import Testing:** Validates that all required Python packages are importable

### Troubleshooting Installation Issues

#### FFmpeg Not Found

If the setup script reports FFmpeg is not installed:

- **Windows:** Install via Chocolatey (`choco install ffmpeg`) or download binaries from [ffmpeg.org](https://ffmpeg.org/download.html)
- **Linux:** `sudo apt install ffmpeg` (Ubuntu/Debian), `sudo yum install ffmpeg` (RHEL/CentOS)
- **macOS:** `brew install ffmpeg`

After installation, restart your terminal and verify: `ffmpeg -version`

#### CUDA Not Available

If PyTorch reports CUDA is not available but you have an NVIDIA GPU:

1. **Verify NVIDIA drivers:** Run `nvidia-smi` to check driver installation
2. **Check CUDA version compatibility:** Ensure your driver supports the CUDA version in PyTorch
3. **Reinstall PyTorch with correct CUDA version:**
   ```powershell
   # Example: Install PyTorch with CUDA 11.8
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

#### Import Errors

If the setup script reports import errors:

1. **Activate the environment first:**
   - Windows: `.\venv\Scripts\Activate.ps1`
   - Linux/macOS: `source venv/bin/activate`
2. **Reinstall dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Check Python version:** TalkSmith requires Python 3.10 or 3.11
   ```bash
   python --version
   ```

#### Virtual Environment Creation Failed

If virtual environment creation fails:

1. **Ensure Python is installed:** `python --version`
2. **Install venv module (Linux):** `sudo apt install python3-venv`
3. **Try alternative Python command:**
   - Use `python3` instead of `python`
   - Use specific version: `python3.11 -m venv venv`

### Next Steps After Installation

Once installation is complete:

1. **Verify setup:**
   ```bash
   python scripts/check_gpu.py
   python scripts/check_ffmpeg.py
   ```

2. **Prefetch models (optional but recommended):**
   ```bash
   # Windows
   .\scripts\prefetch_models.ps1 -Sizes "medium.en,large-v3"

   # Linux/macOS
   ./scripts/prefetch_models.sh --sizes "medium.en,large-v3"
   ```

3. **Try the CLI:**
   ```bash
   python cli/main.py demo
   python cli/main.py export --help
   ```

4. **Read the documentation:**
   - [Configuration Guide](docs/configuration.md)
   - [Diarization Guide](docs/diarization.md)
   - [Testing Guide](TESTING.md)

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

# Generate PRD/plan from transcript - ✅ IMPLEMENTED
python pipeline/plan_from_transcript.py --input segments.json --output plan.md

# Generate and publish to Google Docs - ✅ IMPLEMENTED
python pipeline/plan_from_transcript.py --input segments.json --google-docs --google-docs-title "Project Plan"
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
│   ├── plan_from_transcript.py # ✅ LLM-powered PRD/plan generation
│   ├── google_docs_integration.py # ✅ Google Docs API integration
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
│   ├── consent_template.md    # Recording consent template
│   └── google_docs_setup.md   # ✅ Google Docs integration setup guide
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

## 📝 Plan/PRD Generation

**✅ IMPLEMENTED** - LLM-powered structured plan generation with Google Docs integration

The `plan_from_transcript.py` module extracts structured information from meeting transcripts and generates professional PRD/plan documents using AI.

### Features

- **LLM-powered extraction** - Uses Claude or GPT to intelligently extract plan sections
- **Structured sections** - Problem Statement, Target Users, Goals, Acceptance Criteria, Risks
- **Google Docs publishing** - Optionally upload plans directly to Google Docs
- **Markdown output** - Clean, shareable format
- **Flexible configuration** - Support for multiple LLM providers

### Usage

```python
from pipeline.plan_from_transcript import PlanGenerator

# Initialize with preferred LLM (Claude or GPT)
generator = PlanGenerator(model_type='claude')

# Generate plan from transcript segments
plan_md = generator.generate_plan(
    segments_path='segments.json',
    output_path='plan.md',
    title='Project Plan'
)
```

### CLI Usage

```bash
# Generate local markdown plan (using Claude by default)
python pipeline/plan_from_transcript.py --input segments.json --output plan.md

# Use GPT instead of Claude
python pipeline/plan_from_transcript.py --input segments.json --model gpt

# Generate and upload to Google Docs
python pipeline/plan_from_transcript.py \
    --input segments.json \
    --google-docs \
    --google-docs-title "Q4 Product Roadmap"

# Custom title and both local + Google Docs
python pipeline/plan_from_transcript.py \
    --input segments.json \
    --output plan.md \
    --title "Sprint Planning" \
    --google-docs \
    --google-docs-title "Sprint 23 Plan"
```

### Environment Setup

Set your LLM API key:

```bash
# For Claude (recommended)
export ANTHROPIC_API_KEY="sk-ant-..."

# For GPT
export OPENAI_API_KEY="sk-..."
```

### Google Docs Integration

For Google Docs publishing, complete the setup steps in [docs/google_docs_setup.md](docs/google_docs_setup.md):

1. Create Google Cloud project
2. Enable Google Docs and Drive APIs
3. Download OAuth credentials
4. Configure `config/google_docs.ini`
5. Authenticate on first run

See [README_GOOGLE_DOCS.md](README_GOOGLE_DOCS.md) for detailed documentation.

### Example Output

The generated plan includes:

```markdown
# Project Plan

**Date:** 2025-10-17
**Source:** segments.json

## Problem Statement
[LLM-extracted problem description from transcript]

## Target Users
[Identified user personas and stakeholders]

## Goals & Objectives
[Project goals and success metrics]

## Acceptance Criteria
[Requirements and must-haves]

## Risks & Assumptions
[Potential challenges and assumptions]

## Additional Notes
[Action items and next steps]
```

See [examples/sample_plan.md](examples/sample_plan.md) for a complete example.
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
- [x] GPU and CUDA verification
- [x] Python environment setup (make_env.ps1/sh with verification)
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
- [x] Google Drive sync (rclone)
- [x] Alternative diarization (no HF token)
- [x] Plan/PRD generation with LLM and Google Docs integration
- [ ] Benchmark suite

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

## ☁️ Cloud Sync (Google Drive)

**✅ IMPLEMENTED** - Sync transcripts to Google Drive using rclone

TalkSmith can automatically sync transcription outputs to Google Drive for backup, mobile access, or team collaboration.

### Quick Start

1. **Install rclone** - [rclone.org/downloads](https://rclone.org/downloads/)
2. **Configure Google Drive:**
   ```bash
   rclone config
   ```
3. **Run sync:**
   ```bash
   # Linux/macOS
   ./scripts/sync_to_drive.sh

   # Windows
   .\scripts\sync_to_drive.ps1
   ```

### Features

- **Dry-run mode** - Preview changes before syncing (`--dry-run` / `-DryRun`)
- **Automatic exclusions** - Skip temp files, cache, and system files
- **Environment configuration** - Customize remote name, paths via env vars
- **Cross-platform** - Bash script for Linux/macOS, PowerShell for Windows

### Usage Examples

```bash
# Preview sync without making changes
./scripts/sync_to_drive.sh --dry-run

# Sync with custom remote name
export RCLONE_REMOTE_NAME=my-drive
./scripts/sync_to_drive.sh

# Automated sync (cron)
*/30 * * * * cd /path/to/TalkSmith && ./scripts/sync_to_drive.sh
```

See [docs/google-drive-sync.md](docs/google-drive-sync.md) for complete setup guide, automation options, and security considerations.

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
