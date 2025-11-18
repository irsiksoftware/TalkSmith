"""
DEPRECATED: Use pipeline.diarization.WhisperXDiarizer instead.

This module is kept for backwards compatibility only.
All new code should use the pipeline.diarization package.
"""

import warnings

warnings.warn(
    "pipeline.diarize_whisperx is deprecated. "
    "Use pipeline.diarization.WhisperXDiarizer instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Import everything from new location for backwards compatibility
from pipeline.diarization.whisperx import WhisperXDiarizer  # noqa: F401, E402

# Import the old standalone functions for backwards compatibility
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional

import torch


def diarize_file(
    audio_path: str,
    output_dir: Optional[str] = None,
    model_size: str = "base",
    device: str = "cuda",
    language: Optional[str] = None,
    hf_token: Optional[str] = None,
    min_speakers: Optional[int] = None,
    max_speakers: Optional[int] = None,
    vad_onset: float = 0.5,
    vad_offset: float = 0.363,
) -> Dict:
    """
    DEPRECATED: Use pipeline.diarization.cli.diarize_file instead.

    Diarize a single audio file and save outputs.
    """
    from pipeline.diarization.cli import diarize_file as new_diarize_file

    warnings.warn(
        "diarize_file from pipeline.diarize_whisperx is deprecated. "
        "Use pipeline.diarization.cli.diarize_file instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    return new_diarize_file(
        audio_path=audio_path,
        output_dir=output_dir,
        method="whisperx",
        model_size=model_size,
        device=device,
        language=language,
        hf_token=hf_token,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        vad_onset=vad_onset,
        vad_offset=vad_offset,
    )


def main():
    """DEPRECATED: Use python -m pipeline.diarization.cli instead."""
    warnings.warn(
        "Running diarize_whisperx.py directly is deprecated. "
        "Use: python -m pipeline.diarization.cli --whisperx",
        DeprecationWarning,
        stacklevel=2,
    )

    from pipeline.diarization.cli import main as new_main
    return new_main()


if __name__ == "__main__":
    sys.exit(main())
