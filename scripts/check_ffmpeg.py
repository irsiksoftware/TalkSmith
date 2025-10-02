#!/usr/bin/env python3
"""
FFmpeg Verification Script for TalkSmith
Verifies FFmpeg installation and functionality.
"""

import sys
import subprocess
import shutil
from typing import Optional, Tuple


def check_ffmpeg_installed() -> bool:
    """Check if FFmpeg is installed and accessible in PATH."""
    return shutil.which("ffmpeg") is not None


def get_ffmpeg_version() -> Optional[str]:
    """Get FFmpeg version string."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Extract version from first line
            first_line = result.stdout.split("\n")[0]
            return first_line
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def check_ffmpeg_codecs() -> Tuple[bool, bool]:
    """Check for essential audio codecs."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-codecs"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout.lower()
        has_pcm = "pcm_s16le" in output
        has_aac = "aac" in output
        return has_pcm, has_aac
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, False


def check_ffprobe_installed() -> bool:
    """Check if ffprobe is installed and accessible in PATH."""
    return shutil.which("ffprobe") is not None


def print_section(title: str, char: str = "="):
    """Print a section header."""
    print(f"\n{char * 70}")
    print(f"  {title}")
    print(f"{char * 70}\n")


def print_status(label: str, value: any, success: bool = True):
    """Print a status line with color coding."""
    status_symbol = "✓" if success else "✗"
    print(f"  {status_symbol} {label:30s}: {value}")


def main():
    """Main execution function."""
    print("\n" + "=" * 70)
    print("  TalkSmith FFmpeg Verification")
    print("=" * 70)

    success = True

    # Check FFmpeg installation
    print_section("FFmpeg Installation", "-")

    ffmpeg_installed = check_ffmpeg_installed()
    print_status(
        "FFmpeg", "Installed" if ffmpeg_installed else "NOT FOUND", ffmpeg_installed
    )

    if not ffmpeg_installed:
        success = False
        print("\n  ⚠ FFmpeg is not installed or not in PATH")
        print("  ⚠ Please install FFmpeg - see docs/prereqs.md for instructions")
    else:
        version = get_ffmpeg_version()
        if version:
            print_status("Version", version[:60], True)  # Truncate long version string

        ffprobe_installed = check_ffprobe_installed()
        print_status(
            "ffprobe",
            "Installed" if ffprobe_installed else "NOT FOUND",
            ffprobe_installed,
        )

        if not ffprobe_installed:
            success = False
            print("\n  ⚠ ffprobe not found - usually installed with FFmpeg")

    # Check codecs
    if ffmpeg_installed:
        print_section("Audio Codec Support", "-")
        has_pcm, has_aac = check_ffmpeg_codecs()

        print_status("PCM (WAV)", "Supported" if has_pcm else "NOT FOUND", has_pcm)
        print_status("AAC", "Supported" if has_aac else "NOT FOUND", has_aac)

        if not (has_pcm and has_aac):
            success = False
            print("\n  ⚠ Some essential audio codecs are missing")
            print("  ⚠ Please reinstall FFmpeg with full codec support")

    # Test FFmpeg functionality
    if ffmpeg_installed:
        print_section("Functionality Test", "-")
        try:
            # Test a simple audio generation command
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=1000:duration=1",
                    "-f",
                    "null",
                    "-",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                print_status("Audio Processing", "PASSED", True)
                print("    Test: Generated 1-second sine wave")
            else:
                print_status("Audio Processing", "FAILED", False)
                success = False
        except Exception as e:
            print_status("Audio Processing", f"FAILED: {e}", False)
            success = False

    # Summary
    print_section("Summary", "=")

    if success:
        print("  ✓ All checks passed!")
        print("  ✓ FFmpeg is properly installed and functional")
        print("  ✓ TalkSmith can process audio files")
        return 0
    else:
        print("  ✗ FFmpeg verification failed")
        print("  ✗ Please review the errors above")
        print("  ✗ See docs/prereqs.md for installation instructions:")
        print()
        print("     Windows:  choco install ffmpeg")
        print("     Linux:    sudo apt install ffmpeg")
        print("     macOS:    brew install ffmpeg")
        return 1


if __name__ == "__main__":
    sys.exit(main())
