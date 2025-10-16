"""Unit tests for export formats."""

import pytest
from pathlib import Path


@pytest.mark.unit
class TestExports:
    """Tests for various export formats."""

    def test_export_txt(self, sample_segments, temp_dir):
        """Test plain text export."""
        # TODO: Implement when export module exists
        output_file = temp_dir / "output.txt"
        # export_txt(sample_segments, output_file)
        # assert output_file.exists()
        pass

    def test_export_srt(self, sample_segments, temp_dir):
        """Test SRT subtitle export."""
        pass

    def test_export_vtt(self, sample_segments, temp_dir):
        """Test WebVTT export."""
        pass

    def test_export_json(self, sample_segments, temp_dir):
        """Test JSON export."""
        pass

    def test_srt_format_compliance(self, temp_dir):
        """Test SRT follows format specification."""
        # Format: index, timestamps, text, blank line
        pass

    def test_srt_timestamp_format(self):
        """Test SRT timestamp format (HH:MM:SS,mmm)."""
        pass
