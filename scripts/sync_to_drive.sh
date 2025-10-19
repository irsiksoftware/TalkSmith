#!/bin/bash

# TalkSmith - Google Drive Sync Script
# Syncs transcription outputs to Google Drive using rclone

set -e

# Configuration
REMOTE_NAME="${RCLONE_REMOTE_NAME:-gdrive}"
LOCAL_DIR="${RCLONE_LOCAL_DIR:-./data/outputs}"
REMOTE_DIR="${RCLONE_REMOTE_DIR:-TalkSmith/Transcripts}"

# Parse arguments
DRY_RUN=""
VERBOSE=""

for arg in "$@"; do
  case $arg in
    --dry-run)
      DRY_RUN="--dry-run"
      echo "Running in DRY-RUN mode (no changes will be made)"
      ;;
    -v|--verbose)
      VERBOSE="-v"
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --dry-run    Preview changes without uploading"
      echo "  -v, --verbose  Show detailed output"
      echo "  -h, --help   Show this help message"
      echo ""
      echo "Environment variables:"
      echo "  RCLONE_REMOTE_NAME  Remote name (default: gdrive)"
      echo "  RCLONE_LOCAL_DIR    Local directory (default: ./data/outputs)"
      echo "  RCLONE_REMOTE_DIR   Remote directory (default: TalkSmith/Transcripts)"
      exit 0
      ;;
  esac
done

# Check if rclone is installed
if ! command -v rclone &> /dev/null; then
  echo "Error: rclone is not installed"
  echo "Install from: https://rclone.org/install/"
  exit 1
fi

# Check if remote is configured
if ! rclone listremotes | grep -q "^${REMOTE_NAME}:$"; then
  echo "Error: rclone remote '${REMOTE_NAME}' is not configured"
  echo "Run: rclone config"
  exit 1
fi

# Check if local directory exists
if [ ! -d "$LOCAL_DIR" ]; then
  echo "Error: Local directory '$LOCAL_DIR' does not exist"
  exit 1
fi

# Perform sync
echo "Syncing: $LOCAL_DIR -> ${REMOTE_NAME}:${REMOTE_DIR}"

rclone sync "$LOCAL_DIR" "${REMOTE_NAME}:${REMOTE_DIR}" \
  --progress \
  --exclude ".DS_Store" \
  --exclude "*.tmp" \
  --exclude "*.part" \
  --exclude ".cache/" \
  --exclude "__pycache__/" \
  $DRY_RUN \
  $VERBOSE

if [ -n "$DRY_RUN" ]; then
  echo ""
  echo "Dry-run complete. No files were modified."
  echo "Remove --dry-run to perform actual sync."
else
  echo ""
  echo "Sync complete!"
fi
