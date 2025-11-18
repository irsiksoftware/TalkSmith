"""Base class for speaker diarization."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from pipeline.logger import get_logger


@dataclass
class DiarizationResult:
    """Result from diarization process."""

    segments: List[Dict]
    """List of segments with speaker labels"""

    audio_path: str
    """Path to audio file processed"""

    num_speakers: Optional[int] = None
    """Number of speakers detected"""

    processing_time: float = 0.0
    """Processing time in seconds"""

    metadata: Optional[Dict] = None
    """Additional metadata from diarization"""


class BaseDiarizer(ABC):
    """
    Abstract base class for speaker diarization.

    Subclasses must implement:
    - _diarize_implementation(): Core diarization logic
    """

    def __init__(self, logger=None):
        """
        Initialize base diarizer.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger or get_logger(self.__class__.__name__)

    def diarize(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None,
        **kwargs,
    ) -> DiarizationResult:
        """
        Diarize audio file.

        Args:
            audio_path: Path to audio file
            num_speakers: Number of speakers (None for auto-detect)
            **kwargs: Implementation-specific parameters

        Returns:
            DiarizationResult with segments and metadata
        """
        # Validate input
        audio_path_obj = Path(audio_path)
        if not audio_path_obj.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self.logger.info(
            "Starting diarization",
            audio_file=str(audio_path),
            diarizer=self.__class__.__name__,
        )

        # Call implementation
        result = self._diarize_implementation(
            audio_path=audio_path_obj,
            num_speakers=num_speakers,
            **kwargs,
        )

        self.logger.info(
            "Diarization complete",
            segments=len(result.segments),
            processing_time=result.processing_time,
        )

        return result

    @abstractmethod
    def _diarize_implementation(
        self,
        audio_path: Path,
        num_speakers: Optional[int],
        **kwargs,
    ) -> DiarizationResult:
        """
        Implementation-specific diarization logic.

        Args:
            audio_path: Path to audio file
            num_speakers: Number of speakers or None
            **kwargs: Implementation-specific parameters

        Returns:
            DiarizationResult
        """
        pass

    def _format_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Format segments to standard structure.

        Args:
            segments: Raw segments from diarization

        Returns:
            Formatted segments with keys: start, end, speaker, text
        """
        formatted = []
        for seg in segments:
            formatted_seg = {
                "start": seg.get("start", 0.0),
                "end": seg.get("end", 0.0),
                "speaker": seg.get("speaker", "UNKNOWN"),
                "text": seg.get("text", "").strip(),
            }
            formatted.append(formatted_seg)

        return formatted
