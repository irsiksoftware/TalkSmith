#!/bin/bash
#
# TalkSmith Benchmark Suite Runner
# Tests multiple model configurations for RTF and WER metrics
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
QUICK_MODE=false
FULL_MODE=false
MODELS=("tiny" "base" "small" "medium" "large-v3")
DEVICES=("cuda" "cpu")
COMPUTE_TYPES=("float16" "int8")
DIARIZATION_OPTS=("--diarize" "")
TEST_AUDIO_DIR="./benchmarks/test_audio"
OUTPUT_DIR="./benchmarks/results"
GROUND_TRUTH="$TEST_AUDIO_DIR/ground_truth.json"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --full)
            FULL_MODE=true
            shift
            ;;
        --models)
            IFS=',' read -ra MODELS <<< "$2"
            shift 2
            ;;
        --devices)
            IFS=',' read -ra DEVICES <<< "$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --quick            Run quick benchmark (tiny model, 1min sample only)"
            echo "  --full             Run full benchmark suite (all models, all samples)"
            echo "  --models MODEL1,MODEL2  Comma-separated list of models to test"
            echo "  --devices DEV1,DEV2     Comma-separated list of devices (cuda,cpu)"
            echo "  --output DIR       Output directory for results (default: ./benchmarks/results)"
            echo "  --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --quick                    # Fast test on small sample"
            echo "  $0 --full                     # Complete benchmark suite"
            echo "  $0 --models tiny,base         # Test only tiny and base models"
            echo "  $0 --devices cuda             # Test only on GPU"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Set test files based on mode
if [ "$QUICK_MODE" = true ]; then
    TEST_FILES=("sample_1min.wav")
    MODELS=("tiny")
    DEVICES=("cuda")
    COMPUTE_TYPES=("float16")
    DIARIZATION_OPTS=("")
    echo -e "${YELLOW}Running QUICK benchmark mode${NC}"
elif [ "$FULL_MODE" = true ]; then
    TEST_FILES=("sample_1min.wav" "sample_5min.wav" "sample_30min.wav")
    echo -e "${YELLOW}Running FULL benchmark mode${NC}"
else
    TEST_FILES=("sample_1min.wav" "sample_5min.wav")
    echo -e "${YELLOW}Running STANDARD benchmark mode${NC}"
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"
RESULTS_FILE="$OUTPUT_DIR/benchmark_results.jsonl"

# Clear previous results
> "$RESULTS_FILE"

echo -e "${BLUE}TalkSmith Benchmark Suite${NC}"
echo "================================"
echo "Output directory: $OUTPUT_DIR"
echo "Test files: ${TEST_FILES[*]}"
echo "Models: ${MODELS[*]}"
echo "Devices: ${DEVICES[*]}"
echo ""

# Check if test audio files exist
MISSING_FILES=0
for file in "${TEST_FILES[@]}"; do
    if [ ! -f "$TEST_AUDIO_DIR/$file" ]; then
        echo -e "${RED}Warning: Test file not found: $TEST_AUDIO_DIR/$file${NC}"
        echo -e "${YELLOW}Please add test audio files to $TEST_AUDIO_DIR${NC}"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

if [ $MISSING_FILES -gt 0 ]; then
    echo -e "${RED}Missing $MISSING_FILES test file(s). Exiting.${NC}"
    exit 1
fi

# Check if ground truth exists
if [ ! -f "$GROUND_TRUTH" ]; then
    echo -e "${YELLOW}Warning: Ground truth file not found: $GROUND_TRUTH${NC}"
    echo -e "${YELLOW}WER calculation will be skipped${NC}"
fi

# Counter for progress
TOTAL_TESTS=0
COMPLETED_TESTS=0

# Calculate total tests
for model in "${MODELS[@]}"; do
    for device in "${DEVICES[@]}"; do
        for compute in "${COMPUTE_TYPES[@]}"; do
            for diarize in "${DIARIZATION_OPTS[@]}"; do
                for file in "${TEST_FILES[@]}"; do
                    TOTAL_TESTS=$((TOTAL_TESTS + 1))
                done
            done
        done
    done
done

echo -e "${BLUE}Total benchmark configurations: $TOTAL_TESTS${NC}"
echo ""

# Run benchmarks
for model in "${MODELS[@]}"; do
    for device in "${DEVICES[@]}"; do
        for compute in "${COMPUTE_TYPES[@]}"; do
            for diarize in "${DIARIZATION_OPTS[@]}"; do
                for file in "${TEST_FILES[@]}"; do
                    COMPLETED_TESTS=$((COMPLETED_TESTS + 1))

                    # Skip CPU + float16 (not supported)
                    if [ "$device" = "cpu" ] && [ "$compute" = "float16" ]; then
                        echo -e "${YELLOW}[$COMPLETED_TESTS/$TOTAL_TESTS] Skipping: $model/$device/$compute (unsupported)${NC}"
                        continue
                    fi

                    diarize_flag=""
                    diarize_label="no"
                    if [ -n "$diarize" ]; then
                        diarize_flag="$diarize"
                        diarize_label="yes"
                    fi

                    echo -e "${GREEN}[$COMPLETED_TESTS/$TOTAL_TESTS] Testing: $model / $device / $compute / diarization=$diarize_label / $file${NC}"

                    # Build command
                    input_file="$TEST_AUDIO_DIR/$file"
                    output_file="$OUTPUT_DIR/${model}_${device}_${compute}_diarize${diarize_label}_$(basename $file .wav).json"

                    # Run transcription
                    START_TIME=$(date +%s.%N)

                    python pipeline/transcribe_fw.py \
                        --audio "$input_file" \
                        --model "$model" \
                        --device "$device" \
                        --compute_type "$compute" \
                        $diarize_flag \
                        --output "$output_file" \
                        > "$OUTPUT_DIR/run.log" 2>&1 || {
                            echo -e "${RED}Error running benchmark. Check $OUTPUT_DIR/run.log${NC}"
                            continue
                        }

                    END_TIME=$(date +%s.%N)
                    PROCESS_TIME=$(echo "$END_TIME - $START_TIME" | bc)

                    # Extract metrics from output or transcript
                    if [ -f "$output_file" ]; then
                        # Parse audio duration and RTF from log
                        AUDIO_DURATION=$(grep -oP 'Audio duration:\s*\K[\d.]+' "$OUTPUT_DIR/run.log" || echo "0")
                        RTF=$(grep -oP 'RTF:\s*\K[\d.]+' "$OUTPUT_DIR/run.log" || echo "0")

                        if [ "$RTF" = "0" ] && [ "$AUDIO_DURATION" != "0" ]; then
                            RTF=$(echo "$PROCESS_TIME / $AUDIO_DURATION" | bc -l)
                        fi

                        # Store result
                        echo "{\"model\":\"$model\",\"device\":\"$device\",\"compute_type\":\"$compute\",\"diarization\":$([[ -n "$diarize" ]] && echo "true" || echo "false"),\"audio_file\":\"$file\",\"audio_duration\":$AUDIO_DURATION,\"process_time\":$PROCESS_TIME,\"rtf\":$RTF,\"output_file\":\"$output_file\",\"timestamp\":\"$(date -Iseconds)\"}" >> "$RESULTS_FILE"

                        echo -e "  ${BLUE}RTF: $RTF | Process time: ${PROCESS_TIME}s${NC}"
                    else
                        echo -e "${RED}  Error: Output file not created${NC}"
                    fi

                    echo ""
                done
            done
        done
    done
done

echo -e "${GREEN}Benchmark suite completed!${NC}"
echo ""
echo "Results saved to: $RESULTS_FILE"
echo ""

# Generate reports using Python
echo -e "${BLUE}Generating reports...${NC}"

python3 - <<EOF
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from benchmarks.metrics import BenchmarkResult, generate_report, load_ground_truth, calculate_wer

# Load results
results = []
with open('$RESULTS_FILE', 'r') as f:
    for line in f:
        if line.strip():
            data = json.loads(line)

            # Try to load transcript and calculate WER
            wer = None
            if Path('$GROUND_TRUTH').exists():
                try:
                    ground_truth = load_ground_truth(Path('$GROUND_TRUTH'))
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
                memory_mb=None,  # Could be extracted from GPU monitoring
                timestamp=data['timestamp']
            )
            results.append(result)

# Generate reports
generate_report(results, Path('$OUTPUT_DIR'))

print(f"\n✓ Reports generated in $OUTPUT_DIR/")
print(f"  - report.csv (machine-readable)")
print(f"  - report.json (detailed metrics)")
print(f"  - report.md (human-readable summary)")
EOF

echo ""
echo -e "${GREEN}Done! Check $OUTPUT_DIR/report.md for results.${NC}"
