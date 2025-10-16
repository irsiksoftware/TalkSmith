"""
Alternative speaker diarization using Resemblyzer embeddings + spectral clustering.

This module provides token-free diarization for environments without HuggingFace
token access. Uses speaker embeddings from Resemblyzer and spectral clustering
to identify speakers without requiring pyannote.audio.

Usage:
    python pipeline/diarize_alt.py <audio_file> -o segments.json

Example:
    python pipeline/diarize_alt.py data/samples/interview.wav -o output.json
    python pipeline/diarize_alt.py audio.wav --num-speakers 3 --window-size 2.0
"""

import argparse
import json
import time
import warnings
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

try:
    from resemblyzer import VoiceEncoder, preprocess_wav
    from sklearn.cluster import SpectralClustering
    import librosa
except ImportError as e:
    raise ImportError(
        "Alternative diarization requires additional dependencies. "
        "Install with: pip install resemblyzer scikit-learn librosa\n"
        f"Missing: {e.name}"
    ) from e

from pipeline.logger import get_logger

# Suppress warnings from resemblyzer and sklearn
warnings.filterwarnings("ignore", category=UserWarning)


class AlternativeDiarizer:
    """
    Token-free speaker diarization using Resemblyzer embeddings.

    This approach:
    1. Splits audio into fixed-size windows
    2. Extracts speaker embeddings for each window using Resemblyzer
    3. Clusters embeddings using spectral clustering
    4. Assigns speaker labels to segments
    """

    def __init__(
        self,
        window_size: float = 1.5,
        overlap: float = 0.5,
        min_segment_duration: float = 0.3,
        logger=None,
    ):
        """
        Initialize the diarizer.

        Args:
            window_size: Window size in seconds for embedding extraction
            overlap: Overlap ratio between windows (0.0 to 1.0)
            min_segment_duration: Minimum segment duration in seconds
            logger: Optional logger instance
        """
        self.window_size = window_size
        self.overlap = overlap
        self.min_segment_duration = min_segment_duration
        self.logger = logger or get_logger(__name__)

        self.logger.info(
            "Initializing alternative diarizer",
            window_size=window_size,
            overlap=overlap,
            min_segment_duration=min_segment_duration,
        )

        # Initialize voice encoder
        self.encoder = VoiceEncoder()

    def diarize(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None,
        transcript_segments: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        Perform speaker diarization on audio file.

        Args:
            audio_path: Path to audio file
            num_speakers: Number of speakers (None for auto-detection)
            transcript_segments: Optional transcript segments to align with

        Returns:
            List of segments with speaker labels
        """
        start_time = time.time()

        # Load and preprocess audio
        self.logger.info("Loading audio", audio_path=audio_path)
        wav = preprocess_wav(audio_path)

        # Load audio with librosa for duration
        y, sr = librosa.load(audio_path, sr=16000)
        duration = librosa.get_duration(y=y, sr=sr)

        # Extract embeddings
        self.logger.info("Extracting speaker embeddings")
        embeddings, timestamps = self._extract_embeddings(wav, sr=16000)

        # Cluster speakers
        if num_speakers is None:
            num_speakers = self._estimate_num_speakers(embeddings)
            self.logger.info("Estimated number of speakers", num_speakers=num_speakers)
        else:
            self.logger.info(
                "Using specified number of speakers", num_speakers=num_speakers
            )

        speaker_labels = self._cluster_embeddings(embeddings, num_speakers)

        # Create segments
        segments = self._create_segments(timestamps, speaker_labels, duration)

        # Merge consecutive segments from same speaker
        segments = self._merge_segments(segments)

        # If transcript segments provided, align speakers
        if transcript_segments:
            segments = self._align_with_transcript(segments, transcript_segments)

        elapsed = time.time() - start_time
        self.logger.info(
            "Diarization complete",
            duration=duration,
            processing_time=elapsed,
            num_segments=len(segments),
            num_speakers=num_speakers,
        )

        return segments

    def _extract_embeddings(
        self, wav: np.ndarray, sr: int = 16000
    ) -> tuple[np.ndarray, List[float]]:
        """
        Extract speaker embeddings from audio using sliding windows.

        Args:
            wav: Preprocessed audio waveform
            sr: Sample rate

        Returns:
            Tuple of (embeddings array, timestamps list)
        """
        window_samples = int(self.window_size * sr)
        hop_samples = int(window_samples * (1 - self.overlap))

        embeddings = []
        timestamps = []

        for i in range(0, len(wav) - window_samples, hop_samples):
            window = wav[i: i + window_samples]

            # Skip silent/very quiet windows
            if np.abs(window).max() < 0.01:
                continue

            # Extract embedding
            embedding = self.encoder.embed_utterance(window)
            embeddings.append(embedding)

            # Store window center timestamp
            timestamp = (i + window_samples / 2) / sr
            timestamps.append(timestamp)

        return np.array(embeddings), timestamps

    def _estimate_num_speakers(self, embeddings: np.ndarray) -> int:
        """
        Estimate number of speakers using embedding variance.

        Args:
            embeddings: Speaker embeddings array

        Returns:
            Estimated number of speakers (2-6)
        """
        # Simple heuristic: try different cluster counts and pick best silhouette score
        from sklearn.metrics import silhouette_score

        best_score = -1
        best_n = 2

        for n in range(2, min(7, len(embeddings))):
            clustering = SpectralClustering(
                n_clusters=n, affinity="nearest_neighbors", random_state=42
            )
            labels = clustering.fit_predict(embeddings)

            # Need at least 2 samples per cluster for silhouette score
            if len(set(labels)) < n:
                continue

            score = silhouette_score(embeddings, labels)
            if score > best_score:
                best_score = score
                best_n = n

        return best_n

    def _cluster_embeddings(
        self, embeddings: np.ndarray, num_speakers: int
    ) -> np.ndarray:
        """
        Cluster embeddings into speaker groups.

        Args:
            embeddings: Speaker embeddings array
            num_speakers: Number of speakers

        Returns:
            Array of speaker labels
        """
        clustering = SpectralClustering(
            n_clusters=num_speakers,
            affinity="nearest_neighbors",
            random_state=42,
            n_neighbors=min(10, len(embeddings) - 1),
        )

        labels = clustering.fit_predict(embeddings)
        return labels

    def _create_segments(
        self, timestamps: List[float], labels: np.ndarray, duration: float
    ) -> List[Dict]:
        """
        Create segments from timestamps and speaker labels.

        Args:
            timestamps: List of window center timestamps
            labels: Speaker labels for each window
            duration: Total audio duration

        Returns:
            List of segment dictionaries
        """
        segments = []

        if len(timestamps) == 0:
            return segments

        current_speaker = labels[0]
        segment_start = max(0, timestamps[0] - self.window_size / 2)

        for i in range(1, len(timestamps)):
            # Speaker change detected
            if labels[i] != current_speaker:
                segment_end = (timestamps[i - 1] + timestamps[i]) / 2

                segments.append(
                    {
                        "start": segment_start,
                        "end": segment_end,
                        "speaker": f"SPEAKER_{int(current_speaker):02d}",
                    }
                )

                current_speaker = labels[i]
                segment_start = segment_end

        # Add final segment
        segment_end = min(duration, timestamps[-1] + self.window_size / 2)
        segments.append(
            {
                "start": segment_start,
                "end": segment_end,
                "speaker": f"SPEAKER_{int(current_speaker):02d}",
            }
        )

        return segments

    def _merge_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Merge consecutive segments from the same speaker.

        Args:
            segments: List of segments

        Returns:
            Merged segments
        """
        if not segments:
            return []

        merged = [segments[0]]

        for segment in segments[1:]:
            last = merged[-1]

            # Same speaker and close in time - merge
            if (
                segment["speaker"] == last["speaker"]
                and segment["start"] - last["end"] < 0.5
            ):
                last["end"] = segment["end"]
            else:
                merged.append(segment)

        # Filter out very short segments
        merged = [
            seg
            for seg in merged
            if (seg["end"] - seg["start"]) >= self.min_segment_duration
        ]

        return merged

    def _align_with_transcript(
        self, speaker_segments: List[Dict], transcript_segments: List[Dict]
    ) -> List[Dict]:
        """
        Align speaker diarization with transcript segments.

        Args:
            speaker_segments: Segments with speaker labels
            transcript_segments: Segments with transcript text

        Returns:
            Transcript segments with aligned speaker labels
        """
        aligned = []

        for trans_seg in transcript_segments:
            trans_start = trans_seg["start"]
            trans_end = trans_seg["end"]

            # Find speaker segment with most overlap
            best_speaker = "SPEAKER_00"
            best_overlap = 0

            for spk_seg in speaker_segments:
                overlap_start = max(trans_start, spk_seg["start"])
                overlap_end = min(trans_end, spk_seg["end"])
                overlap = max(0, overlap_end - overlap_start)

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker = spk_seg["speaker"]

            # Create aligned segment
            aligned_seg = trans_seg.copy()
            aligned_seg["speaker"] = best_speaker
            aligned.append(aligned_seg)

        return aligned


def diarize_file(
    audio_path: str,
    output_path: Optional[str] = None,
    num_speakers: Optional[int] = None,
    transcript_path: Optional[str] = None,
    window_size: float = 1.5,
) -> List[Dict]:
    """
    Diarize audio file and save results.

    Args:
        audio_path: Path to audio file
        output_path: Output JSON path (default: <audio_stem>_diarized.json)
        num_speakers: Number of speakers (None for auto-detection)
        transcript_path: Optional path to transcript JSON for alignment
        window_size: Window size in seconds for embedding extraction

    Returns:
        List of diarized segments
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Load transcript if provided
    transcript_segments = None
    if transcript_path:
        transcript_path = Path(transcript_path)
        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {transcript_path}")

        with open(transcript_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            transcript_segments = data.get("segments", data)

    # Initialize diarizer
    diarizer = AlternativeDiarizer(window_size=window_size)

    # Perform diarization
    print(f"Diarizing {audio_path.name}...")
    segments = diarizer.diarize(
        str(audio_path),
        num_speakers=num_speakers,
        transcript_segments=transcript_segments,
    )

    # Determine output path
    if output_path is None:
        output_path = audio_path.parent / f"{audio_path.stem}_diarized.json"
    else:
        output_path = Path(output_path)

    # Save results
    output_data = {
        "audio_file": str(audio_path),
        "num_speakers": len(set(seg["speaker"] for seg in segments)),
        "num_segments": len(segments),
        "segments": segments,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print("\nDiarization Results:")
    print(f"  Speakers detected: {output_data['num_speakers']}")
    print(f"  Segments created: {output_data['num_segments']}")
    print(f"  Saved to: {output_path}")

    return segments


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Alternative speaker diarization (no HF token required)"
    )
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument(
        "-o", "--output", help="Output JSON path (default: <audio>_diarized.json)"
    )
    parser.add_argument(
        "--num-speakers",
        type=int,
        help="Number of speakers (default: auto-detect)",
    )
    parser.add_argument(
        "--transcript",
        help="Path to transcript JSON for alignment with diarization",
    )
    parser.add_argument(
        "--window-size",
        type=float,
        default=1.5,
        help="Window size in seconds for embedding extraction (default: 1.5)",
    )

    args = parser.parse_args()

    try:
        diarize_file(
            args.audio,
            output_path=args.output,
            num_speakers=args.num_speakers,
            transcript_path=args.transcript,
            window_size=args.window_size,
        )
    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
