"""Integration tests for export functionality with full workflow."""

import json
from pathlib import Path

import pytest

from pipeline.exporters import export_all, export_json, export_srt, export_txt, export_vtt


@pytest.mark.integration
class TestExportWorkflow:
    """Integration tests for export workflow with realistic scenarios."""

    def test_complete_export_workflow(self, temp_dir):
        """Test complete export workflow from segments to all formats."""
        # Realistic segments with word-level timestamps
        segments = [
            {
                "start": 0.0,
                "end": 3.5,
                "text": "Welcome to the meeting.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "Welcome", "start": 0.0, "end": 0.5},
                    {"word": "to", "start": 0.6, "end": 0.7},
                    {"word": "the", "start": 0.8, "end": 0.9},
                    {"word": "meeting", "start": 1.0, "end": 1.5},
                ],
            },
            {
                "start": 4.0,
                "end": 8.2,
                "text": "Today we'll discuss the quarterly results.",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "Today", "start": 4.0, "end": 4.3},
                    {"word": "we'll", "start": 4.4, "end": 4.7},
                    {"word": "discuss", "start": 4.8, "end": 5.3},
                    {"word": "the", "start": 5.4, "end": 5.5},
                    {"word": "quarterly", "start": 5.6, "end": 6.2},
                    {"word": "results", "start": 6.3, "end": 6.8},
                ],
            },
            {
                "start": 8.5,
                "end": 12.0,
                "text": "That sounds great. I have the data ready.",
                "speaker": "SPEAKER_01",
            },
        ]

        # Export to all formats
        output_files = export_all(segments, temp_dir, "meeting-transcript")

        # Verify all files created
        assert output_files["txt"].exists()
        assert output_files["srt"].exists()
        assert output_files["vtt"].exists()
        assert output_files["json"].exists()

        # Verify TXT content
        txt_content = output_files["txt"].read_text(encoding="utf-8")
        assert "SPEAKER_00: Welcome to the meeting." in txt_content
        assert "SPEAKER_01: That sounds great." in txt_content

        # Verify SRT format
        srt_content = output_files["srt"].read_text(encoding="utf-8")
        assert "1\n" in srt_content
        assert "00:00:00,000 --> 00:00:03,500" in srt_content
        assert "2\n" in srt_content

        # Verify VTT format
        vtt_content = output_files["vtt"].read_text(encoding="utf-8")
        assert vtt_content.startswith("WEBVTT\n\n")
        assert "00:00:00.000 --> 00:00:03.500" in vtt_content

        # Verify JSON structure
        with open(output_files["json"], encoding="utf-8") as f:
            json_data = json.load(f)
        assert len(json_data["segments"]) == 3
        assert json_data["segments"][0]["words"][0]["word"] == "Welcome"

    def test_multi_speaker_conversation(self, temp_dir):
        """Test export with complex multi-speaker conversation."""
        segments = [
            {
                "start": 0.0,
                "end": 2.0,
                "text": "Hello everyone!",
                "speaker": "SPEAKER_00",
            },
            {
                "start": 2.5,
                "end": 4.0,
                "text": "Hi there!",
                "speaker": "SPEAKER_01",
            },
            {
                "start": 4.2,
                "end": 6.5,
                "text": "Good morning!",
                "speaker": "SPEAKER_02",
            },
            {
                "start": 7.0,
                "end": 10.0,
                "text": "Let's get started.",
                "speaker": "SPEAKER_00",
            },
        ]

        output_file = temp_dir / "conversation.srt"
        export_srt(segments, output_file, include_speakers=True)

        content = output_file.read_text(encoding="utf-8")
        assert "SPEAKER_00: Hello everyone!" in content
        assert "SPEAKER_01: Hi there!" in content
        assert "SPEAKER_02: Good morning!" in content

    def test_long_form_content_export(self, temp_dir):
        """Test export of long-form content (podcast, interview)."""
        # Simulate 1 hour of content
        segments = []
        for i in range(60):  # 60 segments, ~1 minute each
            start_time = i * 60.0
            end_time = start_time + 55.0
            segments.append(
                {
                    "start": start_time,
                    "end": end_time,
                    "text": f"This is segment {i+1} of the long-form content.",
                    "speaker": f"SPEAKER_{i % 3:02d}",
                }
            )

        output_file = temp_dir / "podcast.vtt"
        export_vtt(segments, output_file, include_speakers=True)

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")

        # Check timestamps for hours (segment 0 and segment 59)
        assert "00:00:00.000 --> 00:00:55.000" in content
        assert "00:59:00.000 --> 00:59:55.000" in content

    def test_unicode_multilingual_export(self, temp_dir):
        """Test export with multilingual Unicode content."""
        segments = [
            {"start": 0.0, "end": 2.0, "text": "Hello World", "speaker": "SPEAKER_00"},
            {"start": 2.5, "end": 4.5, "text": "你好世界", "speaker": "SPEAKER_01"},
            {
                "start": 5.0,
                "end": 7.0,
                "text": "مرحبا بالعالم",
                "speaker": "SPEAKER_02",
            },
            {"start": 7.5, "end": 9.5, "text": "Привет мир", "speaker": "SPEAKER_03"},
            {
                "start": 10.0,
                "end": 12.0,
                "text": "こんにちは世界",
                "speaker": "SPEAKER_04",
            },
            {"start": 12.5, "end": 14.5, "text": "🌍🌎🌏", "speaker": "SPEAKER_05"},
        ]

        # Test all formats handle Unicode
        for fmt in ["txt", "srt", "vtt", "json"]:
            output_files = export_all(segments, temp_dir, f"multilingual-{fmt}", formats=[fmt])
            output_file = output_files[fmt]
            content = output_file.read_text(encoding="utf-8")

            assert "你好世界" in content
            assert "مرحبا بالعالم" in content
            assert "Привет мир" in content
            assert "こんにちは世界" in content
            assert "🌍🌎🌏" in content

    def test_export_with_missing_optional_fields(self, temp_dir):
        """Test export gracefully handles segments with missing optional fields."""
        segments = [
            {
                "start": 0.0,
                "end": 2.0,
                "text": "No speaker field",
            },  # Missing speaker
            {
                "start": 2.5,
                "end": 4.5,
                "text": "Has speaker",
                "speaker": "SPEAKER_00",
            },
            {
                "start": 5.0,
                "end": 7.0,
                "text": "No words",
                "speaker": "SPEAKER_01",
            },  # Missing words
        ]

        # Should not raise errors
        output_files = export_all(segments, temp_dir, "partial-data")

        # Verify JSON handles missing fields correctly
        with open(output_files["json"], encoding="utf-8") as f:
            data = json.load(f)

        assert "speaker" not in data["segments"][0]
        assert "speaker" in data["segments"][1]
        assert "words" not in data["segments"][2]

    def test_export_directory_structure(self, temp_dir):
        """Test export creates proper directory structure for organized output."""
        base_dir = temp_dir / "transcripts"
        date_dir = base_dir / "2025-01-15"

        segments = [{"start": 0.0, "end": 2.0, "text": "Test content", "speaker": "SPEAKER_00"}]

        output_files = export_all(segments, date_dir, "meeting-001")

        assert date_dir.exists()
        assert (date_dir / "meeting-001.txt").exists()
        assert (date_dir / "meeting-001.srt").exists()
        assert (date_dir / "meeting-001.vtt").exists()
        assert (date_dir / "meeting-001.json").exists()

    def test_selective_format_export(self, temp_dir):
        """Test exporting only selected formats based on use case."""
        segments = [{"start": 0.0, "end": 2.0, "text": "Test content", "speaker": "SPEAKER_00"}]

        # Video subtitles only
        video_files = export_all(
            segments, temp_dir / "video", "video-subtitle", formats=["srt", "vtt"]
        )
        assert len(video_files) == 2
        assert "srt" in video_files
        assert "vtt" in video_files

        # Data export only
        data_files = export_all(segments, temp_dir / "data", "data-export", formats=["json"])
        assert len(data_files) == 1
        assert "json" in data_files

        # Human-readable only
        text_files = export_all(segments, temp_dir / "text", "readable", formats=["txt"])
        assert len(text_files) == 1
        assert "txt" in text_files


@pytest.mark.integration
class TestExportEdgeCases:
    """Integration tests for edge cases in real-world scenarios."""

    def test_rapid_speaker_changes(self, temp_dir):
        """Test export handles rapid speaker turn-taking."""
        segments = []
        for i in range(20):
            segments.append(
                {
                    "start": i * 0.5,
                    "end": (i + 1) * 0.5,
                    "text": f"Word {i}",
                    "speaker": f"SPEAKER_{i % 2:02d}",
                }
            )

        output_file = temp_dir / "rapid-turns.srt"
        export_srt(segments, output_file, include_speakers=True)

        content = output_file.read_text(encoding="utf-8")
        assert "SPEAKER_00:" in content
        assert "SPEAKER_01:" in content

    def test_very_long_transcript_text(self, temp_dir):
        """Test export handles very long text in segments."""
        long_text = " ".join(["word"] * 500)  # 500-word segment
        segments = [{"start": 0.0, "end": 300.0, "text": long_text}]

        output_files = export_all(segments, temp_dir, "long-text")

        # Verify all formats handle long text
        for path in output_files.values():
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "word" in content

    def test_export_preserves_punctuation(self, temp_dir):
        """Test export preserves special punctuation and formatting."""
        segments = [
            {"start": 0.0, "end": 2.0, "text": "Hello! How are you?", "speaker": "A"},
            {"start": 2.5, "end": 4.5, "text": "I'm fine, thanks.", "speaker": "B"},
            {"start": 5.0, "end": 7.0, "text": "Great! Let's go...", "speaker": "A"},
        ]

        output_file = temp_dir / "punctuation.txt"
        export_txt(segments, output_file)

        content = output_file.read_text(encoding="utf-8")
        assert "Hello! How are you?" in content
        assert "I'm fine, thanks." in content
        assert "Great! Let's go..." in content

    def test_word_level_timestamps_export(self, temp_dir):
        """Test JSON export includes detailed word-level timestamps."""
        segments = [
            {
                "start": 0.0,
                "end": 2.0,
                "text": "Testing word timestamps",
                "speaker": "SPEAKER_00",
                "words": [
                    {"word": "Testing", "start": 0.0, "end": 0.5},
                    {"word": "word", "start": 0.6, "end": 1.0},
                    {"word": "timestamps", "start": 1.1, "end": 1.9},
                ],
            }
        ]

        output_file = temp_dir / "words.json"
        export_json(segments, output_file, include_words=True)

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)

        words = data["segments"][0]["words"]
        assert len(words) == 3
        assert words[0]["word"] == "Testing"
        assert words[0]["start"] == 0.0
        assert words[2]["word"] == "timestamps"


@pytest.mark.integration
class TestExportCompatibility:
    """Integration tests for format compatibility with external tools."""

    def test_srt_subtitle_player_compatibility(self, temp_dir):
        """Test SRT format is compatible with standard subtitle players."""
        segments = [
            {"start": 0.0, "end": 2.5, "text": "First subtitle", "speaker": "A"},
            {"start": 3.0, "end": 5.5, "text": "Second subtitle", "speaker": "B"},
        ]

        output_file = temp_dir / "player.srt"
        export_srt(segments, output_file, include_speakers=False)

        content = output_file.read_text(encoding="utf-8")
        lines = content.strip().split("\n")

        # Validate SRT structure
        assert lines[0] == "1"  # First index
        assert "-->" in lines[1]  # Timestamp line
        assert lines[2] == "First subtitle"  # Text
        assert lines[3] == ""  # Blank line

    def test_vtt_webvtt_spec_compliance(self, temp_dir):
        """Test VTT format complies with WebVTT specification."""
        segments = [{"start": 0.0, "end": 2.0, "text": "WebVTT test", "speaker": "SPEAKER_00"}]

        output_file = temp_dir / "webvtt.vtt"
        export_vtt(segments, output_file, include_speakers=True)

        content = output_file.read_text(encoding="utf-8")

        # WebVTT spec: must start with "WEBVTT"
        assert content.startswith("WEBVTT\n\n")

        # WebVTT uses period for milliseconds
        assert "." in content
        assert "," not in content.split("\n")[3]  # Not in timestamp line

    def test_json_api_compatibility(self, temp_dir):
        """Test JSON format is compatible with API consumption."""
        segments = [
            {
                "start": 0.0,
                "end": 2.0,
                "text": "API test",
                "speaker": "SPEAKER_00",
                "words": [{"word": "API", "start": 0.0, "end": 0.5}],
            }
        ]

        output_file = temp_dir / "api.json"
        export_json(segments, output_file, pretty=False)

        # Verify it's valid JSON
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)

        # Verify structure suitable for API
        assert "segments" in data
        assert isinstance(data["segments"], list)
        assert all(isinstance(s, dict) for s in data["segments"])
