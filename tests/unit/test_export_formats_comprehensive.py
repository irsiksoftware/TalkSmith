"""Comprehensive unit tests for export formats module.

This test suite provides full coverage for pipeline/exporters.py including:
- Timestamp formatting (SRT and VTT formats)
- Segment validation
- All export formats (TXT, SRT, VTT, JSON)
- Edge cases and error handling
- Unicode support
"""

import json
import pytest
from pathlib import Path
from pipeline.exporters import (
    format_timestamp_srt,
    format_timestamp_vtt,
    validate_segments,
    export_txt,
    export_srt,
    export_vtt,
    export_json,
    export_all,
)


@pytest.mark.unit
class TestTimestampFormatting:
    """Tests for timestamp formatting functions."""

    def test_format_timestamp_srt_zero(self):
        """Test SRT timestamp format at 0 seconds."""
        assert format_timestamp_srt(0.0) == "00:00:00,000"

    def test_format_timestamp_srt_basic(self):
        """Test SRT timestamp format for basic time."""
        assert format_timestamp_srt(65.5) == "00:01:05,500"

    def test_format_timestamp_srt_hours(self):
        """Test SRT timestamp format with hours."""
        assert format_timestamp_srt(3661.123) == "01:01:01,123"

    def test_format_timestamp_srt_milliseconds(self):
        """Test SRT timestamp millisecond precision."""
        assert format_timestamp_srt(1.999) == "00:00:01,999"

    def test_format_timestamp_vtt_zero(self):
        """Test VTT timestamp format at 0 seconds."""
        assert format_timestamp_vtt(0.0) == "00:00:00.000"

    def test_format_timestamp_vtt_basic(self):
        """Test VTT timestamp format for basic time."""
        assert format_timestamp_vtt(65.5) == "00:01:05.500"

    def test_format_timestamp_vtt_hours(self):
        """Test VTT timestamp format with hours."""
        assert format_timestamp_vtt(3661.123) == "01:01:01.123"

    def test_format_timestamp_vtt_uses_period(self):
        """Test VTT uses period separator (not comma like SRT)."""
        result = format_timestamp_vtt(1.5)
        assert "." in result
        assert "," not in result


@pytest.mark.unit
class TestSegmentValidation:
    """Tests for segment validation."""

    def test_validate_segments_valid(self, sample_segments):
        """Test validation passes for valid segments."""
        validate_segments(sample_segments)  # Should not raise

    def test_validate_segments_not_list(self):
        """Test validation fails if segments is not a list."""
        with pytest.raises(ValueError, match="Segments must be a list"):
            validate_segments("not a list")

    def test_validate_segments_item_not_dict(self):
        """Test validation fails if segment item is not a dict."""
        with pytest.raises(ValueError, match="Segment 0 must be a dictionary"):
            validate_segments([123])

    def test_validate_segments_missing_start(self):
        """Test validation fails if segment missing start timestamp."""
        with pytest.raises(ValueError, match="Segment 0 missing 'start'"):
            validate_segments([{"end": 1.0, "text": "test"}])

    def test_validate_segments_missing_end(self):
        """Test validation fails if segment missing end timestamp."""
        with pytest.raises(ValueError, match="Segment 0 missing.*'end'"):
            validate_segments([{"start": 0.0, "text": "test"}])

    def test_validate_segments_missing_text(self):
        """Test validation fails if segment missing text field."""
        with pytest.raises(ValueError, match="Segment 0 missing 'text'"):
            validate_segments([{"start": 0.0, "end": 1.0}])

    def test_validate_segments_non_numeric_timestamp(self):
        """Test validation fails for non-numeric timestamps."""
        with pytest.raises(ValueError, match="Segment 0 timestamps must be numeric"):
            validate_segments([{"start": "0.0", "end": 1.0, "text": "test"}])

    def test_validate_segments_negative_timestamp(self):
        """Test validation fails for negative timestamps."""
        with pytest.raises(ValueError, match="Segment 0 has negative timestamp"):
            validate_segments([{"start": -1.0, "end": 1.0, "text": "test"}])

    def test_validate_segments_start_after_end(self):
        """Test validation fails if start time is after end time."""
        with pytest.raises(ValueError, match="Segment 0 has start time after end time"):
            validate_segments([{"start": 5.0, "end": 1.0, "text": "test"}])

    def test_validate_segments_integer_timestamps(self):
        """Test validation accepts integer timestamps."""
        segments = [{"start": 0, "end": 5, "text": "test"}]
        validate_segments(segments)  # Should not raise


@pytest.mark.unit
class TestExportTxt:
    """Tests for plain text export."""

    def test_export_txt_creates_file(self, sample_segments, temp_dir):
        """Test TXT export creates output file."""
        output_file = temp_dir / "output.txt"
        export_txt(sample_segments, output_file)
        assert output_file.exists()

    def test_export_txt_with_timestamps_and_speakers(self, sample_segments, temp_dir):
        """Test TXT export includes timestamps and speaker labels."""
        output_file = temp_dir / "output.txt"
        export_txt(
            sample_segments, output_file, include_timestamps=True, include_speakers=True
        )
        content = output_file.read_text(encoding="utf-8")
        assert "[00:00:00.000 --> 00:00:02.500]" in content
        assert "SPEAKER_00:" in content
        assert "Hello, this is a test." in content

    def test_export_txt_without_timestamps(self, sample_segments, temp_dir):
        """Test TXT export without timestamps."""
        output_file = temp_dir / "output.txt"
        export_txt(
            sample_segments,
            output_file,
            include_timestamps=False,
            include_speakers=True,
        )
        content = output_file.read_text(encoding="utf-8")
        assert "[" not in content  # No timestamp markers
        assert "SPEAKER_00:" in content

    def test_export_txt_without_speakers(self, sample_segments, temp_dir):
        """Test TXT export without speaker labels."""
        output_file = temp_dir / "output.txt"
        export_txt(
            sample_segments,
            output_file,
            include_timestamps=True,
            include_speakers=False,
        )
        content = output_file.read_text(encoding="utf-8")
        assert "SPEAKER_00:" not in content
        assert "Hello, this is a test." in content

    def test_export_txt_creates_parent_dirs(self, sample_segments, temp_dir):
        """Test TXT export creates parent directories if needed."""
        output_file = temp_dir / "subdir" / "nested" / "output.txt"
        export_txt(sample_segments, output_file)
        assert output_file.exists()

    def test_export_txt_unicode_support(self, temp_dir):
        """Test TXT export handles Unicode characters."""
        segments = [
            {"start": 0.0, "end": 1.0, "text": "Hello 世界 🌍", "speaker": "SPEAKER_00"}
        ]
        output_file = temp_dir / "unicode.txt"
        export_txt(segments, output_file)
        content = output_file.read_text(encoding="utf-8")
        assert "Hello 世界 🌍" in content


@pytest.mark.unit
class TestExportSrt:
    """Tests for SRT subtitle export."""

    def test_export_srt_creates_file(self, sample_segments, temp_dir):
        """Test SRT export creates output file."""
        output_file = temp_dir / "output.srt"
        export_srt(sample_segments, output_file)
        assert output_file.exists()

    def test_export_srt_format_compliance(self, sample_segments, temp_dir):
        """Test SRT follows format specification: index, timestamps, text, blank line."""
        output_file = temp_dir / "output.srt"
        export_srt(sample_segments, output_file)
        content = output_file.read_text(encoding="utf-8")
        lines = content.split("\n")
        # First subtitle block
        assert lines[0] == "1"
        assert "00:00:00,000 --> 00:00:02,500" in lines[1]
        assert "SPEAKER_00: Hello, this is a test." in lines[2]
        assert lines[3] == ""  # Blank line

    def test_export_srt_timestamp_format(self, sample_segments, temp_dir):
        """Test SRT timestamp format uses comma separator (HH:MM:SS,mmm)."""
        output_file = temp_dir / "output.srt"
        export_srt(sample_segments, output_file)
        content = output_file.read_text(encoding="utf-8")
        assert "00:00:00,000 --> 00:00:02,500" in content
        assert "00:00:03,000 --> 00:00:05,500" in content

    def test_export_srt_sequential_numbering(self, sample_segments, temp_dir):
        """Test SRT uses sequential numbering starting from 1."""
        output_file = temp_dir / "output.srt"
        export_srt(sample_segments, output_file)
        content = output_file.read_text(encoding="utf-8")
        assert content.startswith("1\n")
        assert "\n2\n" in content

    def test_export_srt_with_speakers(self, sample_segments, temp_dir):
        """Test SRT includes speaker labels when requested."""
        output_file = temp_dir / "output.srt"
        export_srt(sample_segments, output_file, include_speakers=True)
        content = output_file.read_text(encoding="utf-8")
        assert "SPEAKER_00:" in content
        assert "SPEAKER_01:" in content

    def test_export_srt_without_speakers(self, sample_segments, temp_dir):
        """Test SRT excludes speaker labels when not requested."""
        output_file = temp_dir / "output.srt"
        export_srt(sample_segments, output_file, include_speakers=False)
        content = output_file.read_text(encoding="utf-8")
        assert "SPEAKER_00:" not in content
        assert "Hello, this is a test." in content

    def test_export_srt_segment_without_speaker(self, temp_dir):
        """Test SRT handles segments without speaker field."""
        segments = [{"start": 0.0, "end": 1.0, "text": "No speaker here"}]
        output_file = temp_dir / "output.srt"
        export_srt(segments, output_file, include_speakers=True)
        content = output_file.read_text(encoding="utf-8")
        assert "No speaker here" in content
        assert ":" not in content.split("\n")[2]  # No speaker label


@pytest.mark.unit
class TestExportVtt:
    """Tests for WebVTT export."""

    def test_export_vtt_creates_file(self, sample_segments, temp_dir):
        """Test VTT export creates output file."""
        output_file = temp_dir / "output.vtt"
        export_vtt(sample_segments, output_file)
        assert output_file.exists()

    def test_export_vtt_header(self, sample_segments, temp_dir):
        """Test VTT file starts with WEBVTT header."""
        output_file = temp_dir / "output.vtt"
        export_vtt(sample_segments, output_file)
        content = output_file.read_text(encoding="utf-8")
        assert content.startswith("WEBVTT\n\n")

    def test_export_vtt_timestamp_format(self, sample_segments, temp_dir):
        """Test VTT uses period separator (not comma)."""
        output_file = temp_dir / "output.vtt"
        export_vtt(sample_segments, output_file)
        content = output_file.read_text(encoding="utf-8")
        assert "00:00:00.000 --> 00:00:02.500" in content
        assert "," not in content.split("\n")[3]  # No commas in timestamps

    def test_export_vtt_with_speakers(self, sample_segments, temp_dir):
        """Test VTT includes speaker as cue identifier."""
        output_file = temp_dir / "output.vtt"
        export_vtt(sample_segments, output_file, include_speakers=True)
        content = output_file.read_text(encoding="utf-8")
        # VTT format: speaker on its own line before timestamp
        assert "SPEAKER_00\n00:00:00.000" in content

    def test_export_vtt_without_speakers(self, sample_segments, temp_dir):
        """Test VTT excludes speaker labels when not requested."""
        output_file = temp_dir / "output.vtt"
        export_vtt(sample_segments, output_file, include_speakers=False)
        content = output_file.read_text(encoding="utf-8")
        assert "SPEAKER_00" not in content
        assert "Hello, this is a test." in content


@pytest.mark.unit
class TestExportJson:
    """Tests for JSON export."""

    def test_export_json_creates_file(self, sample_segments, temp_dir):
        """Test JSON export creates output file."""
        output_file = temp_dir / "output.json"
        export_json(sample_segments, output_file)
        assert output_file.exists()

    def test_export_json_valid_structure(self, sample_segments, temp_dir):
        """Test JSON export produces valid JSON with correct structure."""
        output_file = temp_dir / "output.json"
        export_json(sample_segments, output_file)
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
        assert "segments" in data
        assert len(data["segments"]) == 2
        assert data["segments"][0]["start"] == 0.0
        assert data["segments"][0]["end"] == 2.5
        assert data["segments"][0]["text"] == "Hello, this is a test."

    def test_export_json_includes_speakers(self, sample_segments, temp_dir):
        """Test JSON includes speaker information."""
        output_file = temp_dir / "output.json"
        export_json(sample_segments, output_file)
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
        assert data["segments"][0]["speaker"] == "SPEAKER_00"

    def test_export_json_includes_words(self, sample_segments, temp_dir):
        """Test JSON includes word-level timestamps when available."""
        output_file = temp_dir / "output.json"
        export_json(sample_segments, output_file, include_words=True)
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
        assert "words" in data["segments"][0]
        assert len(data["segments"][0]["words"]) == 5
        assert data["segments"][0]["words"][0]["word"] == "Hello"

    def test_export_json_excludes_words(self, sample_segments, temp_dir):
        """Test JSON excludes word-level data when not requested."""
        output_file = temp_dir / "output.json"
        export_json(sample_segments, output_file, include_words=False)
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
        assert "words" not in data["segments"][0]

    def test_export_json_pretty_format(self, sample_segments, temp_dir):
        """Test JSON pretty printing with indentation."""
        output_file = temp_dir / "output.json"
        export_json(sample_segments, output_file, pretty=True)
        content = output_file.read_text(encoding="utf-8")
        assert "  " in content  # Has indentation
        assert "\n" in content  # Has newlines

    def test_export_json_compact_format(self, sample_segments, temp_dir):
        """Test JSON compact format without indentation."""
        output_file = temp_dir / "output.json"
        export_json(sample_segments, output_file, pretty=False)
        content = output_file.read_text(encoding="utf-8")
        # Compact format has fewer newlines and no indentation
        assert content.count("\n") < 5  # Very few newlines

    def test_export_json_unicode_support(self, temp_dir):
        """Test JSON export handles Unicode without ASCII escaping."""
        segments = [
            {"start": 0.0, "end": 1.0, "text": "Hello 世界 🌍", "speaker": "SPEAKER_00"}
        ]
        output_file = temp_dir / "unicode.json"
        export_json(segments, output_file)
        content = output_file.read_text(encoding="utf-8")
        assert "Hello 世界 🌍" in content
        assert "\\u" not in content  # ensure_ascii=False


@pytest.mark.unit
class TestExportAll:
    """Tests for export_all function."""

    def test_export_all_default_formats(self, sample_segments, temp_dir):
        """Test export_all creates all default formats."""
        output_files = export_all(sample_segments, temp_dir, "test")
        assert len(output_files) == 4
        assert "txt" in output_files
        assert "srt" in output_files
        assert "vtt" in output_files
        assert "json" in output_files
        for path in output_files.values():
            assert path.exists()

    def test_export_all_custom_formats(self, sample_segments, temp_dir):
        """Test export_all with custom format selection."""
        output_files = export_all(
            sample_segments, temp_dir, "test", formats=["txt", "json"]
        )
        assert len(output_files) == 2
        assert "txt" in output_files
        assert "json" in output_files
        assert "srt" not in output_files

    def test_export_all_file_naming(self, sample_segments, temp_dir):
        """Test export_all uses correct base name and extensions."""
        output_files = export_all(sample_segments, temp_dir, "my_transcript")
        assert output_files["txt"].name == "my_transcript.txt"
        assert output_files["srt"].name == "my_transcript.srt"
        assert output_files["vtt"].name == "my_transcript.vtt"
        assert output_files["json"].name == "my_transcript.json"

    def test_export_all_creates_output_dir(self, sample_segments, temp_dir):
        """Test export_all creates output directory if it doesn't exist."""
        output_dir = temp_dir / "new" / "nested" / "dir"
        output_files = export_all(sample_segments, output_dir, "test")
        assert output_dir.exists()
        for path in output_files.values():
            assert path.parent == output_dir

    def test_export_all_invalid_format(self, sample_segments, temp_dir):
        """Test export_all raises error for unknown format."""
        with pytest.raises(ValueError, match="Unknown format: invalid"):
            export_all(sample_segments, temp_dir, "test", formats=["invalid"])

    def test_export_all_returns_paths(self, sample_segments, temp_dir):
        """Test export_all returns dict mapping formats to file paths."""
        output_files = export_all(sample_segments, temp_dir, "test")
        assert isinstance(output_files, dict)
        assert all(isinstance(p, Path) for p in output_files.values())


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_segments_list(self, temp_dir):
        """Test export handles empty segments list."""
        segments = []
        output_file = temp_dir / "empty.txt"
        export_txt(segments, output_file)
        content = output_file.read_text(encoding="utf-8")
        assert content == ""

    def test_single_segment(self, temp_dir):
        """Test export handles single segment."""
        segments = [{"start": 0.0, "end": 1.0, "text": "Single segment"}]
        output_file = temp_dir / "single.txt"
        export_txt(segments, output_file)
        content = output_file.read_text(encoding="utf-8")
        assert "Single segment" in content

    def test_long_duration_timestamp(self, temp_dir):
        """Test timestamp formatting for long durations (multiple hours)."""
        segments = [
            {"start": 7265.5, "end": 7270.0, "text": "Two hours in"}
        ]  # 2h 1m 5.5s
        output_file = temp_dir / "long.srt"
        export_srt(segments, output_file)
        content = output_file.read_text(encoding="utf-8")
        assert "02:01:05,500" in content

    def test_zero_duration_segment(self, temp_dir):
        """Test segment with zero duration (start == end)."""
        segments = [{"start": 1.0, "end": 1.0, "text": "Zero duration"}]
        output_file = temp_dir / "zero.txt"
        export_txt(segments, output_file)  # Should not raise
        assert output_file.exists()

    def test_very_short_segment(self, temp_dir):
        """Test very short segment (milliseconds)."""
        segments = [{"start": 0.001, "end": 0.002, "text": "Quick"}]
        output_file = temp_dir / "quick.srt"
        export_srt(segments, output_file)
        content = output_file.read_text(encoding="utf-8")
        assert "00:00:00,001 --> 00:00:00,002" in content

    def test_segment_without_words_field(self, temp_dir):
        """Test JSON export with segment missing words field."""
        segments = [
            {"start": 0.0, "end": 1.0, "text": "No words", "speaker": "SPEAKER_00"}
        ]
        output_file = temp_dir / "nowords.json"
        export_json(segments, output_file, include_words=True)
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
        assert "words" not in data["segments"][0]

    def test_overlapping_segments(self, temp_dir):
        """Test export handles overlapping speech segments."""
        segments = [
            {
                "start": 0.0,
                "end": 2.0,
                "text": "First speaker",
                "speaker": "SPEAKER_00",
            },
            {
                "start": 1.5,
                "end": 3.0,
                "text": "Overlapping speech",
                "speaker": "SPEAKER_01",
            },
        ]
        output_file = temp_dir / "overlap.srt"
        export_srt(segments, output_file)  # Should handle gracefully
        assert output_file.exists()
