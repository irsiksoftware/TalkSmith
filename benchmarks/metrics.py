"""
Benchmark metrics calculation utilities for TalkSmith.

This module provides functions to calculate performance metrics:
- RTF (Real-Time Factor): speed of transcription
- WER (Word Error Rate): accuracy of transcription
"""

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class BenchmarkResult:
    """Container for benchmark results."""

    model: str
    device: str
    compute_type: str
    diarization: bool
    audio_file: str
    audio_duration: float
    process_time: float
    rtf: float
    wer: Optional[float]
    memory_mb: Optional[float]
    timestamp: str


def calculate_rtf(audio_duration: float, process_time: float) -> float:
    """
    Calculate Real-Time Factor (RTF).

    RTF = process_time / audio_duration

    RTF < 1.0 means faster than real-time
    RTF = 1.0 means real-time processing
    RTF > 1.0 means slower than real-time

    Args:
        audio_duration: Duration of audio in seconds
        process_time: Time taken to process in seconds

    Returns:
        Real-Time Factor as a float
    """
    if audio_duration <= 0:
        raise ValueError("Audio duration must be positive")
    return process_time / audio_duration


def normalize_text(text: str) -> str:
    """
    Normalize text for WER calculation.

    - Convert to lowercase
    - Remove punctuation
    - Normalize whitespace
    - Strip leading/trailing whitespace

    Args:
        text: Input text to normalize

    Returns:
        Normalized text
    """
    # Convert to lowercase
    text = text.lower()

    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # Strip
    text = text.strip()

    return text


def calculate_wer(reference: str, hypothesis: str) -> float:
    """
    Calculate Word Error Rate (WER).

    WER = (S + D + I) / N
    where:
        S = number of substitutions
        D = number of deletions
        I = number of insertions
        N = number of words in reference

    Uses Levenshtein distance at word level.

    Args:
        reference: Ground truth transcript
        hypothesis: Generated transcript

    Returns:
        WER as a float (0.0 = perfect, 1.0 = completely wrong)
    """
    # Normalize both texts
    ref_normalized = normalize_text(reference)
    hyp_normalized = normalize_text(hypothesis)

    # Split into words
    ref_words = ref_normalized.split()
    hyp_words = hyp_normalized.split()

    # Calculate Levenshtein distance
    n = len(ref_words)
    m = len(hyp_words)

    if n == 0:
        return 0.0 if m == 0 else 1.0

    # Create DP table
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    # Initialize base cases
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    # Fill DP table
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(
                    dp[i - 1][j] + 1,  # Deletion
                    dp[i][j - 1] + 1,  # Insertion
                    dp[i - 1][j - 1] + 1,  # Substitution
                )

    # WER is edit distance divided by reference length
    wer = dp[n][m] / n
    return wer


def load_ground_truth(ground_truth_path: Path) -> Dict[str, str]:
    """
    Load ground truth transcripts from JSON file.

    Args:
        ground_truth_path: Path to ground_truth.json

    Returns:
        Dictionary mapping audio filenames to reference transcripts
    """
    with open(ground_truth_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_report(results: List[BenchmarkResult], output_dir: Path) -> None:
    """
    Generate benchmark reports in multiple formats.

    Creates:
    - report.csv: Machine-readable CSV
    - report.json: Detailed JSON with all metrics
    - report.md: Human-readable markdown summary

    Args:
        results: List of benchmark results
        output_dir: Directory to save reports
    """
    if not results:
        print("No results to report")
        return

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert to DataFrame
    df = pd.DataFrame([asdict(r) for r in results])

    # Save CSV
    csv_path = output_dir / "report.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved CSV report to {csv_path}")

    # Save JSON
    json_path = output_dir / "report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    print(f"Saved JSON report to {json_path}")

    # Generate markdown report
    md_path = output_dir / "report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# TalkSmith Benchmark Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Summary statistics
        f.write("## Summary Statistics\n\n")
        f.write(f"- **Total Benchmarks:** {len(results)}\n")
        f.write(f"- **Models Tested:** {', '.join(df['model'].unique())}\n")
        f.write(f"- **Devices:** {', '.join(df['device'].unique())}\n\n")

        # Detailed results table
        f.write("## Detailed Results\n\n")

        # Group by audio file for cleaner presentation
        for audio_file in df["audio_file"].unique():
            f.write(f"### {audio_file}\n\n")

            subset = df[df["audio_file"] == audio_file].copy()

            # Format the table
            f.write(
                "| Model | Device | Compute | Diarization | RTF | WER | "
                "Memory (MB) | Process Time (s) |\n"
            )
            f.write(
                "|-------|--------|---------|-------------|-----|-----|"
                "-------------|------------------|\n"
            )

            for _, row in subset.iterrows():
                wer_str = f"{row['wer']:.2%}" if pd.notna(row["wer"]) else "N/A"
                mem_str = f"{row['memory_mb']:.1f}" if pd.notna(row["memory_mb"]) else "N/A"
                diar_str = "Yes" if row["diarization"] else "No"

                f.write(
                    f"| {row['model']} | {row['device']} | {row['compute_type']} | "
                    f"{diar_str} | {row['rtf']:.3f} | {wer_str} | {mem_str} | "
                    f"{row['process_time']:.1f} |\n"
                )

            f.write("\n")

        # Best configurations
        f.write("## Best Configurations\n\n")

        f.write("### Fastest (Lowest RTF)\n")
        fastest = df.nsmallest(3, "rtf")[["model", "device", "compute_type", "rtf"]]
        f.write(fastest.to_markdown(index=False))
        f.write("\n\n")

        if df["wer"].notna().any():
            f.write("### Most Accurate (Lowest WER)\n")
            most_accurate = df[df["wer"].notna()].nsmallest(3, "wer")[["model", "device", "wer"]]
            f.write(most_accurate.to_markdown(index=False))
            f.write("\n\n")

        # Trade-off analysis
        if df["wer"].notna().any():
            f.write("## Speed vs Accuracy Trade-off\n\n")
            f.write("Models ranked by balanced performance (lower is better):\n\n")

            # Calculate composite score (normalized RTF + WER)
            valid_rows = df[df["wer"].notna()].copy()
            if len(valid_rows) > 0:
                valid_rows["score"] = (
                    valid_rows["rtf"] / valid_rows["rtf"].max()
                    + valid_rows["wer"] / valid_rows["wer"].max()
                )
                top_balanced = valid_rows.nsmallest(5, "score")[
                    ["model", "device", "rtf", "wer", "score"]
                ]
                f.write(top_balanced.to_markdown(index=False))
                f.write("\n")

    print(f"Saved Markdown report to {md_path}")


def parse_transcription_output(output: str) -> tuple[float, float]:
    """
    Parse RTF and process time from transcription output.

    Looks for lines like:
    - "RTF: 0.123"
    - "Processing time: 45.67s"

    Args:
        output: Raw output from transcription script

    Returns:
        Tuple of (rtf, process_time)
    """
    rtf = None
    process_time = None

    for line in output.split("\n"):
        rtf_match = re.search(r"RTF:\s*([\d.]+)", line, re.IGNORECASE)
        if rtf_match:
            rtf = float(rtf_match.group(1))

        time_match = re.search(r"Processing time:\s*([\d.]+)\s*s", line, re.IGNORECASE)
        if time_match:
            process_time = float(time_match.group(1))

    return rtf, process_time
