"""
Diarization utilities for TalkSmith.

Provides base class and implementations for speaker diarization.
"""

from pipeline.diarization.base import BaseDiarizer, DiarizationResult

# Lazy imports to avoid errors when dependencies not installed
__all__ = [
    "BaseDiarizer",
    "DiarizationResult",
    "WhisperXDiarizer",
    "AlternativeDiarizer",
]


def __getattr__(name):
    """Lazy import for diarizer implementations."""
    if name == "WhisperXDiarizer":
        from pipeline.diarization.whisperx import WhisperXDiarizer
        return WhisperXDiarizer
    elif name == "AlternativeDiarizer":
        from pipeline.diarization.alternative import AlternativeDiarizer
        return AlternativeDiarizer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
