"""
Base class for speaker diarization implementations.

Provides common functionality for all diarizers including:
- Logger initialization and management
- Audio file validation
- Output path resolution and JSON serialization
- Statistics printing and performance tracking
- CLI scaffolding with argparse
"""

import argparse
import json
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipeline.logger import get_logger


class DiarizationBase(ABC):
    """
    Abstract base class for speaker diarization.

    Subclasses must implement:
    - _initialize_models(): Initialize model-specific resources
    - _perform_diarization(): Core diarization logic
    - _get_cli_parser(): CLI argument parser setup
    """

    def __init__(self, logger=None, **kwargs):
        """
        Initialize base diarizer.

        Args:
            logger: Optional logger instance
            **kwargs: Additional configuration parameters (stored for subclasses)
        """
        self.logger = logger or get_logger(__name__)
        self._config = kwargs

        # Let subclasses initialize their models
        self._initialize_models()

    @abstractmethod
    def _initialize_models(self):
        """
        Initialize model-specific resources.

        Subclasses should load models, configure devices, etc.
        This is called automatically during __init__.
        """
        pass

    @abstractmethod
    def _perform_diarization(
        self, audio_path: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Perform the actual diarization.

        Args:
            audio_path: Path to audio file
            **kwargs: Implementation-specific parameters

        Returns:
            Dictionary with diarization results. Must include 'segments' key
            with list of segments containing start, end, and speaker fields.
        """
        pass

    @classmethod
    @abstractmethod
    def _get_cli_parser(cls) -> argparse.ArgumentParser:
        """
        Get CLI argument parser for this diarizer.

        Returns:
            ArgumentParser configured with diarizer-specific arguments
        """
        pass

    @staticmethod
    def validate_audio_file(audio_path: str) -> Path:
        """
        Validate that audio file exists.

        Args:
            audio_path: Path to audio file

        Returns:
            Path object for the audio file

        Raises:
            FileNotFoundError: If audio file doesn't exist
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        return audio_path

    @staticmethod
    def resolve_output_path(
        audio_path: Path,
        output_arg: Optional[str] = None,
        suffix: str = "_diarized",
        extension: str = ".json",
    ) -> Path:
        """
        Resolve output file path.

        Args:
            audio_path: Input audio file path
            output_arg: Optional output path from CLI/API
            suffix: Suffix to add to filename (default: '_diarized')
            extension: File extension (default: '.json')

        Returns:
            Resolved output path
        """
        if output_arg:
            output_path = Path(output_arg)
        else:
            output_path = audio_path.parent / f"{audio_path.stem}{suffix}{extension}"

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    @staticmethod
    def save_json(data: Dict[str, Any], output_path: Path):
        """
        Save data to JSON file.

        Args:
            data: Dictionary to serialize
            output_path: Output file path
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_json(input_path: Path) -> Dict[str, Any]:
        """
        Load data from JSON file.

        Args:
            input_path: Input file path

        Returns:
            Loaded dictionary
        """
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def print_statistics(self, result: Dict[str, Any], audio_path: Path):
        """
        Print diarization statistics.

        Args:
            result: Diarization results dictionary
            audio_path: Path to audio file
        """
        segments = result.get("segments", [])

        print(f"\nDiarization Results for {audio_path.name}:")

        # Duration and processing time
        if "duration" in result:
            print(f"  Duration: {result['duration']:.2f}s")
        if "processing_time" in result:
            print(f"  Processing time: {result['processing_time']:.2f}s")
        if "rtf" in result:
            print(f"  RTF: {result['rtf']:.3f}")

        # Language (if available)
        if "language" in result:
            print(f"  Language: {result['language']}")

        # Segments
        print(f"  Segments: {len(segments)}")

        # Count unique speakers
        speakers = set()
        for segment in segments:
            if "speaker" in segment:
                speakers.add(segment["speaker"])

        if speakers:
            print(f"  Speakers detected: {len(speakers)}")

    def save_text_output(self, result: Dict[str, Any], output_path: Path):
        """
        Save human-readable text output with speaker labels.

        Args:
            result: Diarization results dictionary
            output_path: Output file path
        """
        segments = result.get("segments", [])

        with open(output_path, "w", encoding="utf-8") as f:
            for segment in segments:
                speaker = segment.get("speaker", "UNKNOWN")
                text = segment.get("text", "")

                if text:
                    f.write(f"[{speaker}] {text}\n")
                else:
                    # For diarizers that don't produce text
                    start = segment.get("start", 0.0)
                    end = segment.get("end", 0.0)
                    f.write(f"[{speaker}] {start:.2f}s - {end:.2f}s\n")

    def diarize_with_timing(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """
        Perform diarization with timing information.

        Args:
            audio_path: Path to audio file
            **kwargs: Implementation-specific parameters

        Returns:
            Diarization results with added timing information
        """
        start_time = time.time()

        result = self._perform_diarization(audio_path, **kwargs)

        # Add processing time if not already present
        if "processing_time" not in result:
            result["processing_time"] = time.time() - start_time

        # Calculate RTF if duration is available
        if "duration" in result and "processing_time" in result:
            duration = result["duration"]
            if duration > 0:
                result["rtf"] = result["processing_time"] / duration

        return result

    def diarize_file(
        self,
        audio_path: str,
        output_dir: Optional[str] = None,
        save_json: bool = True,
        save_text: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Diarize audio file and save outputs.

        Args:
            audio_path: Path to audio file
            output_dir: Optional output directory (default: same as input)
            save_json: Whether to save JSON output
            save_text: Whether to save text output
            **kwargs: Implementation-specific diarization parameters

        Returns:
            Diarization results dictionary
        """
        # Validate input
        audio_path = self.validate_audio_file(audio_path)

        # Determine output directory
        if output_dir:
            output_base = Path(output_dir)
            output_base.mkdir(parents=True, exist_ok=True)
        else:
            output_base = audio_path.parent

        # Perform diarization
        self.logger.info("Starting diarization", audio_path=str(audio_path))
        print(f"\nDiarizing {audio_path.name}...")

        result = self.diarize_with_timing(str(audio_path), **kwargs)

        # Print statistics
        self.print_statistics(result, audio_path)

        # Save JSON output
        if save_json:
            json_path = output_base / f"{audio_path.stem}_diarized.json"
            self.save_json(result, json_path)
            print(f"  Saved JSON to: {json_path}")

        # Save text output
        if save_text:
            txt_path = output_base / f"{audio_path.stem}_diarized.txt"
            self.save_text_output(result, txt_path)
            print(f"  Saved text to: {txt_path}")

        return result

    @classmethod
    def run_cli(cls):
        """
        Run CLI interface for this diarizer.

        Uses the parser from _get_cli_parser() and handles common
        error cases.
        """
        parser = cls._get_cli_parser()
        args = parser.parse_args()

        try:
            # Extract common arguments
            audio_path = args.audio
            output_dir = getattr(args, "output_dir", None)

            # Get diarizer-specific kwargs
            diarizer_kwargs = cls._extract_diarizer_kwargs(args)

            # Get diarization-specific kwargs
            diarization_kwargs = cls._extract_diarization_kwargs(args)

            # Initialize diarizer
            diarizer = cls(**diarizer_kwargs)

            # Run diarization
            diarizer.diarize_file(
                audio_path,
                output_dir=output_dir,
                **diarization_kwargs,
            )

            return 0

        except Exception as e:
            print(f"Error: {e}")
            return 1

    @classmethod
    def _extract_diarizer_kwargs(cls, args: argparse.Namespace) -> Dict[str, Any]:
        """
        Extract constructor kwargs from parsed arguments.

        Subclasses can override to customize which args go to __init__.

        Args:
            args: Parsed command-line arguments

        Returns:
            Dictionary of kwargs for diarizer constructor
        """
        # Default: pass logger if available
        kwargs = {}
        if hasattr(args, "logger"):
            kwargs["logger"] = args.logger
        return kwargs

    @classmethod
    def _extract_diarization_kwargs(cls, args: argparse.Namespace) -> Dict[str, Any]:
        """
        Extract diarization kwargs from parsed arguments.

        Subclasses can override to customize which args go to diarize().

        Args:
            args: Parsed command-line arguments

        Returns:
            Dictionary of kwargs for diarization
        """
        return {}
