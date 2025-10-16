# Configuration System

TalkSmith uses a centralized configuration system based on `settings.ini` files with support for environment variable overrides and CLI flags.

## Quick Start

### Using Default Configuration

The configuration system will automatically use defaults if no `settings.ini` file is found:

```python
from config import get_config

config = get_config()
model = config.get('Models', 'whisper_model')  # Returns 'large-v3'
```

### Creating a Configuration File

Create a default `settings.ini`:

```bash
python -m config.settings
```

Or specify a custom path:

```bash
python -m config.settings /path/to/custom/settings.ini
```

## Configuration File Location

The configuration system searches for `settings.ini` in the following order:

1. Path specified in `TALKSMITH_CONFIG` environment variable
2. `./settings.ini` (current directory)
3. `./config/settings.ini`
4. `~/.talksmith/settings.ini` (user home directory)

If no file is found, default values are used.

## Configuration Sections

### [Paths]

Directory paths for inputs, outputs, and cache:

```ini
[Paths]
input_dir = data/inputs
output_dir = data/outputs
samples_dir = data/samples
cache_dir = .cache
```

### [Models]

Model selection and configuration:

```ini
[Models]
# Whisper model size: tiny, tiny.en, base, base.en, small, small.en, medium, medium.en, large-v2, large-v3
whisper_model = large-v3

# Device: auto, cuda, cpu
whisper_device = auto

# Compute type: float16, int8, int8_float16, float32
compute_type = float16

# HuggingFace diarization model
diarization_model = pyannote/speaker-diarization-3.1

# Batch processing
batch_size = 16
num_workers = 4
```

### [Diarization]

Speaker diarization settings:

```ini
[Diarization]
# Mode: whisperx, alt (no-token), or off
mode = whisperx

# Voice Activity Detection threshold (0.0-1.0)
vad_threshold = 0.5

# Speaker constraints
min_speakers = 1
max_speakers = 10

# Minimum segment length in seconds
min_segment_length = 0.5
```

### [Export]

Output format configuration:

```ini
[Export]
# Comma-separated list: txt, json, srt, vtt
formats = txt,json,srt

# Include timestamps
include_timestamps = true

# Include confidence scores
include_confidence = true

# Export word-level timestamps (larger files)
word_level = false
```

### [Processing]

Audio preprocessing options:

```ini
[Processing]
denoise = false
normalize_audio = true
trim_silence = false
sample_rate = 16000
```

### [Logging]

Logging configuration:

```ini
[Logging]
# Level: DEBUG, INFO, WARNING, ERROR, CRITICAL
level = INFO

# Format: json or text
format = json

# Directory (supports {slug} placeholder)
log_dir = data/outputs/{slug}/logs

# Console output
console_output = true
```

## Environment Variable Overrides

Override any setting using environment variables with the format:

```
TALKSMITH_<SECTION>_<KEY>=value
```

Examples:

```bash
# Override whisper model
export TALKSMITH_MODELS_WHISPER_MODEL=medium.en

# Override input directory
export TALKSMITH_PATHS_INPUT_DIR=/custom/input/path

# Override diarization mode
export TALKSMITH_DIARIZATION_MODE=off
```

Environment variables take precedence over `settings.ini` values.

## Priority Order

Settings are resolved in the following order (highest to lowest priority):

1. **CLI flags** (handled by the calling script)
2. **Environment variables** (e.g., `TALKSMITH_MODELS_WHISPER_MODEL`)
3. **Configuration file** (`settings.ini`)
4. **Default values** (hardcoded in `config/settings.py`)

## Python API

### Basic Usage

```python
from config import get_config

# Get global config instance (singleton)
config = get_config()

# Get string value
model = config.get('Models', 'whisper_model')

# Get with fallback
custom = config.get('Custom', 'key', fallback='default')
```

### Type-Specific Getters

```python
# Get integer
batch_size = config.get_int('Models', 'batch_size')

# Get float
threshold = config.get_float('Diarization', 'vad_threshold')

# Get boolean
denoise = config.get_bool('Processing', 'denoise')

# Get list (comma-separated)
formats = config.get_list('Export', 'formats')

# Get path (returns Path object)
input_dir = config.get_path('Paths', 'input_dir')

# Get path and create directory if missing
output_dir = config.get_path('Paths', 'output_dir', create=True)
```

### Setting Values

```python
from config import get_config

config = get_config()

# Set value
config.set('Models', 'whisper_model', 'base.en')

# Save to file
config.save()  # Saves to original location

# Save to custom path
config.save('/path/to/custom/settings.ini')
```

### Reload Configuration

```python
from config import get_config

# Force reload (re-reads file and env vars)
config = get_config(reload=True)
```

### Convert to Dictionary

```python
from config import get_config

config = get_config()
config_dict = config.to_dict()

# Returns:
# {
#     'Paths': {'input_dir': 'data/inputs', ...},
#     'Models': {'whisper_model': 'large-v3', ...},
#     ...
# }
```

## Command-Line Usage Examples

### Using Default Config

```bash
python pipeline/transcribe_fw.py audio.wav
# Uses settings from config/settings.ini or defaults
```

### Override with Environment Variables

```bash
TALKSMITH_MODELS_WHISPER_MODEL=medium.en python pipeline/transcribe_fw.py audio.wav
```

### Multiple Overrides

```bash
TALKSMITH_MODELS_WHISPER_MODEL=base.en \
TALKSMITH_DIARIZATION_MODE=off \
python pipeline/transcribe_fw.py audio.wav
```

### Custom Config File

```bash
TALKSMITH_CONFIG=/path/to/custom.ini python pipeline/transcribe_fw.py audio.wav
```

## Best Practices

1. **Use `settings.ini` for project defaults** - Check this into version control
2. **Use environment variables for deployment** - Different settings per environment
3. **Use CLI flags for one-off changes** - Quick experiments and overrides
4. **Create environment-specific configs** - `settings.production.ini`, `settings.dev.ini`

## Example Workflow

1. **Development**: Use default `config/settings.ini` with dev-friendly settings
2. **Testing**: Override with `TALKSMITH_CONFIG=config/settings.test.ini`
3. **Production**: Set environment variables in deployment configuration

## Troubleshooting

### Config File Not Found

If you see default values being used unexpectedly:

```python
from config import get_config

config = get_config()
print(f"Config loaded from: {config.config_path}")
```

### Environment Variables Not Working

Ensure correct format:
- Must start with `TALKSMITH_`
- Section and key in UPPERCASE
- Example: `TALKSMITH_MODELS_WHISPER_MODEL` (not `talksmith_models_whisper_model`)

### Check Current Configuration

```python
from config import get_config

config = get_config()

# Print all settings
import json
print(json.dumps(config.to_dict(), indent=2))
```

## See Also

- [API Documentation](api.md)
- [Pipeline Guide](pipeline.md)
- [CLI Reference](cli.md)
