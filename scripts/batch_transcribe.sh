#!/usr/bin/env bash
# Batch transcribe audio files using TalkSmith
#
# Usage:
#   ./batch_transcribe.sh [options]
#
# Options:
#   --input-dir DIR       Input directory (default: data/inputs)
#   --output-dir DIR      Output directory (default: data/outputs)
#   --model-size SIZE     Model size: tiny|base|small|medium|medium.en|large-v3 (default: base)
#   --device DEVICE       Device: cuda|cpu (default: cuda)
#   --diarization MODE    Diarization: whisperx|alt|off (default: off)
#   --preprocess          Enable audio preprocessing

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Change to root directory
cd "$ROOT_DIR"

# Default values
INPUT_DIR="data/inputs"
OUTPUT_DIR="data/outputs"
MODEL_SIZE="base"
DEVICE="cuda"
DIARIZATION="off"
PREPROCESS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --input-dir)
            INPUT_DIR="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --model-size)
            MODEL_SIZE="$2"
            shift 2
            ;;
        --device)
            DEVICE="$2"
            shift 2
            ;;
        --diarization)
            DIARIZATION="$2"
            shift 2
            ;;
        --preprocess)
            PREPROCESS="--preprocess"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run batch transcribe
python "$SCRIPT_DIR/batch_transcribe.py" \
    --input-dir "$INPUT_DIR" \
    --output-dir "$OUTPUT_DIR" \
    --model-size "$MODEL_SIZE" \
    --device "$DEVICE" \
    --diarization "$DIARIZATION" \
    $PREPROCESS
