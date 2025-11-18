"""
DEPRECATED: Use pipeline.diarization.AlternativeDiarizer instead.

This module is kept for backwards compatibility only.
All new code should use the pipeline.diarization package.
"""

import warnings

warnings.warn(
    "pipeline.diarize_alt is deprecated. "
    "Use pipeline.diarization.AlternativeDiarizer instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Import everything from new location for backwards compatibility
from pipeline.diarization.alternative import AlternativeDiarizer  # noqa: F401, E402

# Import the old standalone functions for backwards compatibility
import sys
from pathlib import Path
from typing import Dict, List, Optional


def diarize_file(
    audio_path: str,
    output_path: Optional[str] = None,
    num_speakers: Optional[int] = None,
    transcript_path: Optional[str] = None,
    window_size: float = 1.5,
) -> List[Dict]:
    """
    DEPRECATED: Use pipeline.diarization.cli.diarize_file instead.

    Diarize audio file and save results.
    """
    from pipeline.diarization.cli import diarize_file as new_diarize_file

    warnings.warn(
        "diarize_file from pipeline.diarize_alt is deprecated. "
        "Use pipeline.diarization.cli.diarize_file instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Determine output directory
    if output_path:
        output_dir = str(Path(output_path).parent)
    else:
        output_dir = None

    result = new_diarize_file(
        audio_path=audio_path,
        output_dir=output_dir,
        method="alt",
        num_speakers=num_speakers,
        transcript_path=transcript_path,
        window_size=window_size,
    )

    # Return just segments for backwards compatibility
    return result.get("segments", result)


def main():
    """DEPRECATED: Use python -m pipeline.diarization.cli instead."""
    warnings.warn(
        "Running diarize_alt.py directly is deprecated. "
        "Use: python -m pipeline.diarization.cli --alt",
        DeprecationWarning,
        stacklevel=2,
    )

    from pipeline.diarization.cli import main as new_main
    return new_main()


if __name__ == "__main__":
    sys.exit(main())
