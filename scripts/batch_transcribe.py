#!/usr/bin/env python3
"""
Batch transcription script for TalkSmith.

Processes all audio files in an input directory with resume capability.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.transcribe_fw import FasterWhisperTranscriber
from pipeline.logger import get_logger, BatchLogSummary


class BatchTranscriber:
    """Batch transcription with resume capability."""

    SUPPORTED_FORMATS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus"}

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        model_size: str = "base",
        device: str = "cuda",
        diarization: str = "off",
        preprocess: bool = False,
    ):
        """
        Initialize batch transcriber.

        Args:
            input_dir: Directory containing audio files
            output_dir: Directory for output files
            model_size: Whisper model size
            device: Device to use (cuda or cpu)
            diarization: Diarization mode (whisperx|alt|off)
            preprocess: Enable audio preprocessing
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.model_size = model_size
        self.device = device
        self.diarization = diarization
        self.preprocess = preprocess

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize logger with batch slug
        slug = f"batch-{Path(input_dir).name}"
        self.logger = get_logger(__name__, slug=slug)
        self.batch_summary = BatchLogSummary(self.logger)

        # Manifest file for tracking progress
        self.manifest_path = self.output_dir / "manifest.csv"

        # Initialize transcriber
        self.transcriber = FasterWhisperTranscriber(
            model_size=model_size, device=device
        )

    def _get_audio_files(self) -> List[Path]:
        """Get all audio files from input directory."""
        audio_files = []
        for ext in self.SUPPORTED_FORMATS:
            audio_files.extend(self.input_dir.glob(f"*{ext}"))
        return sorted(audio_files)

    def _is_completed(self, audio_file: Path) -> bool:
        """Check if audio file has already been transcribed."""
        output_json = self.output_dir / f"{audio_file.stem}.json"
        return output_json.exists()

    def _load_manifest(self) -> dict:
        """Load existing manifest data."""
        manifest = {}
        if self.manifest_path.exists():
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    manifest[row["filename"]] = row
        return manifest

    def _save_manifest_entry(self, entry: dict):
        """Save or update a manifest entry."""
        manifest = self._load_manifest()
        manifest[entry["filename"]] = entry

        # Write updated manifest
        fieldnames = [
            "filename",
            "status",
            "duration",
            "rtf",
            "model_size",
            "device",
            "language",
            "error",
        ]

        with open(self.manifest_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in manifest.values():
                writer.writerow(row)

    def _transcribe_file(self, audio_file: Path) -> dict:
        """
        Transcribe a single file.

        Returns:
            Manifest entry dictionary
        """
        entry = {
            "filename": audio_file.name,
            "status": "processing",
            "duration": "",
            "rtf": "",
            "model_size": self.model_size,
            "device": self.device,
            "language": "",
            "error": "",
        }

        try:
            self.logger.log_start("transcription", audio_file=audio_file.name)

            # Transcribe
            result = self.transcriber.transcribe(str(audio_file))

            # Save outputs
            output_base = self.output_dir / audio_file.stem

            # Save text
            with open(f"{output_base}.txt", "w", encoding="utf-8") as f:
                f.write(result["text"])

            # Save JSON
            with open(f"{output_base}.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            # Update entry
            entry.update(
                {
                    "status": "completed",
                    "duration": f"{result['duration']:.2f}",
                    "rtf": f"{result['rtf']:.3f}",
                    "language": result["language"],
                }
            )

            self.logger.log_complete(
                "transcription",
                duration=result["duration"],
                rtf=result["rtf"],
                language=result["language"],
                audio_file=audio_file.name,
            )
            self.batch_summary.record_success(audio_file.name)

        except Exception as e:
            entry.update({"status": "failed", "error": str(e)})
            self.logger.error(
                f"Failed to transcribe {audio_file.name}",
                audio_file=audio_file.name,
                error=str(e),
            )
            self.batch_summary.record_failure(audio_file.name, str(e))

        return entry

    def run(self) -> int:
        """
        Run batch transcription.

        Returns:
            Exit code (0 for success, 1 if any failures)
        """
        audio_files = self._get_audio_files()

        if not audio_files:
            self.logger.warning(f"No audio files found in {self.input_dir}")
            print(f"No audio files found in {self.input_dir}")
            return 0

        self.logger.info(
            f"Starting batch transcription",
            total_files=len(audio_files),
            model_size=self.model_size,
            device=self.device,
            diarization=self.diarization,
            preprocess=self.preprocess,
        )

        print(f"Found {len(audio_files)} audio file(s)")
        print(f"Model: {self.model_size}")
        print(f"Device: {self.device}")
        print(f"Output: {self.output_dir}")
        print(f"Diarization: {self.diarization}")
        print(f"Preprocess: {self.preprocess}")

        if self.diarization != "off":
            warning_msg = (
                f"Diarization mode '{self.diarization}' "
                "not yet implemented, will skip diarization."
            )
            self.logger.warning(warning_msg, diarization=self.diarization)
            print(f"\n⚠️  Warning: {warning_msg}")

        if self.preprocess:
            warning_msg = "Preprocessing not yet implemented, will skip preprocessing."
            self.logger.warning(warning_msg, preprocess=self.preprocess)
            print(f"\n⚠️  Warning: {warning_msg}")

        print()

        completed = 0
        skipped = 0
        failed = 0

        for i, audio_file in enumerate(audio_files, 1):
            print(f"[{i}/{len(audio_files)}] {audio_file.name}")

            # Skip if already completed
            if self._is_completed(audio_file):
                self.logger.debug(
                    f"Skipping already completed file", audio_file=audio_file.name
                )
                print("  ✓ Already completed, skipping")
                skipped += 1
                continue

            # Transcribe
            entry = self._transcribe_file(audio_file)

            # Save to manifest
            self._save_manifest_entry(entry)

            # Report
            if entry["status"] == "completed":
                print(
                    f"  ✓ Completed in {entry['duration']}s " f"(RTF: {entry['rtf']})"
                )
                completed += 1
            else:
                print(f"  ✗ Failed: {entry['error']}")
                failed += 1

            print()

        # Summary
        self.batch_summary.print_summary()

        print("=" * 60)
        print(f"Batch transcription complete")
        print(f"Total files: {len(audio_files)}")
        print(f"Completed: {completed}")
        print(f"Skipped: {skipped}")
        print(f"Failed: {failed}")
        print(f"Manifest: {self.manifest_path}")

        return self.batch_summary.get_exit_code()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Batch transcribe audio files")
    parser.add_argument(
        "--input-dir",
        default="data/inputs",
        help="Input directory with audio files (default: data/inputs)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/outputs",
        help="Output directory (default: data/outputs)",
    )
    parser.add_argument(
        "--model-size",
        default="base",
        choices=["tiny", "base", "small", "medium", "medium.en", "large-v3"],
        help="Whisper model size (default: base)",
    )
    parser.add_argument(
        "--device",
        default="cuda",
        choices=["cuda", "cpu"],
        help="Device to use (default: cuda)",
    )
    parser.add_argument(
        "--diarization",
        default="off",
        choices=["whisperx", "alt", "off"],
        help="Diarization mode (default: off)",
    )
    parser.add_argument(
        "--preprocess", action="store_true", help="Enable audio preprocessing"
    )

    args = parser.parse_args()

    try:
        batch_transcriber = BatchTranscriber(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            model_size=args.model_size,
            device=args.device,
            diarization=args.diarization,
            preprocess=args.preprocess,
        )

        exit_code = batch_transcriber.run()
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n\nBatch transcription interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger = get_logger(__name__)
        logger.exception("Fatal error in batch transcription")
        print(f"\n\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
