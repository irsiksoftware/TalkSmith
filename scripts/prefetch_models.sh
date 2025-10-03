#!/usr/bin/env bash
#
# Prefetch Whisper and diarization models for TalkSmith
#
# Downloads and caches Whisper models and pyannote diarization models.
# This script helps ensure models are available offline and reduces
# first-run latency.
#
# Usage:
#   ./scripts/prefetch_models.sh [OPTIONS]
#
# Options:
#   --sizes SIZES           Comma-separated list of Whisper model sizes
#                          Default: medium.en,large-v3
#                          Available: tiny, tiny.en, base, base.en, small,
#                                    small.en, medium, medium.en, large-v2, large-v3
#   --cache-dir DIR        Directory to store model cache (default: .cache)
#   --skip-diarization     Skip downloading diarization models
#   --hf-token TOKEN       HuggingFace token for pyannote models
#   --help                 Show this help message
#
# Examples:
#   ./scripts/prefetch_models.sh
#   ./scripts/prefetch_models.sh --sizes "medium.en,large-v3"
#   ./scripts/prefetch_models.sh --skip-diarization
#   ./scripts/prefetch_models.sh --hf-token "hf_xxx"
#
# Model sizes (approximate disk space):
#   - tiny/tiny.en: ~75 MB
#   - base/base.en: ~150 MB
#   - small/small.en: ~500 MB
#   - medium/medium.en: ~1.5 GB
#   - large-v2: ~3 GB
#   - large-v3: ~3 GB
#   - pyannote diarization: ~100 MB

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
SIZES="medium.en,large-v3"
CACHE_DIR=".cache"
SKIP_DIARIZATION=false
HF_TOKEN=""

# Valid model sizes
VALID_SIZES=("tiny" "tiny.en" "base" "base.en" "small" "small.en" "medium" "medium.en" "large-v2" "large-v3")

# Parse arguments
show_help() {
    grep '^#' "$0" | sed '1,2d; s/^# \?//'
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --sizes)
            SIZES="$2"
            shift 2
            ;;
        --cache-dir)
            CACHE_DIR="$2"
            shift 2
            ;;
        --skip-diarization)
            SKIP_DIARIZATION=true
            shift
            ;;
        --hf-token)
            HF_TOKEN="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Display header
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}TalkSmith Model Prefetch Utility${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Parse and validate sizes
IFS=',' read -ra MODEL_SIZES <<< "$SIZES"
for size in "${MODEL_SIZES[@]}"; do
    valid=false
    for valid_size in "${VALID_SIZES[@]}"; do
        if [[ "$size" == "$valid_size" ]]; then
            valid=true
            break
        fi
    done
    if [[ "$valid" == false ]]; then
        echo -e "${RED}Error: Invalid model size '$size'${NC}"
        echo -e "${YELLOW}Valid sizes: ${VALID_SIZES[*]}${NC}"
        exit 1
    fi
done

# Check Python
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python not found. Please install Python 3.10 or 3.11${NC}"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "${GREEN}✓ Python found: $PYTHON_VERSION${NC}"

# Create cache directory
if [[ ! -d "$CACHE_DIR" ]]; then
    mkdir -p "$CACHE_DIR"
    echo -e "${GREEN}✓ Created cache directory: $CACHE_DIR${NC}"
else
    echo -e "${GREEN}✓ Cache directory exists: $CACHE_DIR${NC}"
fi

# Set environment variables for HuggingFace cache
export HF_HOME="$CACHE_DIR"
export TRANSFORMERS_CACHE="$CACHE_DIR/transformers"

echo ""
echo -e "${CYAN}Downloading Whisper models...${NC}"
echo ""

# Download Whisper models
for size in "${MODEL_SIZES[@]}"; do
    echo -e "${YELLOW}Downloading Whisper model: $size${NC}"

    $PYTHON_CMD - <<EOF
import sys
try:
    from faster_whisper import WhisperModel

    # Download model by initializing it
    model = WhisperModel("$size", device="cpu", download_root="$CACHE_DIR")
    print(f"✓ Successfully downloaded: $size")
    sys.exit(0)
except ImportError:
    print("Error: faster-whisper not installed. Run: pip install faster-whisper")
    sys.exit(1)
except Exception as e:
    print(f"Error downloading $size: {e}")
    sys.exit(1)
EOF

    if [[ $? -ne 0 ]]; then
        echo -e "${RED}✗ Failed to download: $size${NC}"
    else
        echo -e "${GREEN}✓ Successfully cached: $size${NC}"
    fi

    echo ""
done

# Download diarization models
if [[ "$SKIP_DIARIZATION" == false ]]; then
    echo -e "${CYAN}Downloading diarization models...${NC}"
    echo ""

    # Set HF token if provided
    if [[ -n "$HF_TOKEN" ]]; then
        export HF_TOKEN="$HF_TOKEN"
        echo -e "${GREEN}✓ Using provided HuggingFace token${NC}"
    elif [[ -n "$HF_TOKEN" ]]; then
        echo -e "${GREEN}✓ Using HuggingFace token from environment${NC}"
    else
        echo -e "${YELLOW}⚠ No HuggingFace token provided. Diarization download may fail.${NC}"
        echo -e "${YELLOW}  Get a token at: https://huggingface.co/settings/tokens${NC}"
        echo -e "${YELLOW}  Accept terms at: https://huggingface.co/pyannote/speaker-diarization-3.1${NC}"
        echo ""
    fi

    $PYTHON_CMD - <<EOF
import sys
import os

try:
    from pyannote.audio import Pipeline

    # Set cache directory
    os.environ['HF_HOME'] = "$CACHE_DIR"

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
    print("3. Set HF_TOKEN environment variable or pass --hf-token parameter")
    sys.exit(1)
EOF

    if [[ $? -ne 0 ]]; then
        echo -e "${RED}✗ Failed to download diarization models${NC}"
        echo -e "${YELLOW}  Use --skip-diarization flag to skip diarization model download${NC}"
    else
        echo -e "${GREEN}✓ Successfully cached diarization models${NC}"
    fi
fi

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}Model prefetch complete!${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "Models cached in: $CACHE_DIR"
echo -e "To use these models, ensure TRANSFORMERS_CACHE=$CACHE_DIR/transformers"
echo ""
