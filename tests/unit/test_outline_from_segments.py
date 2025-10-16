"""Tests for outline generation from segments."""

import pytest
from pipeline.outline_from_segments import (
    format_timestamp_anchor,
    extract_key_phrases,
    detect_topic_change,
    generate_outline,
    format_outline_markdown,
)


@pytest.fixture
def sample_segments():
    """Sample segments for outline generation."""
    return [
        {
            "start": 0.0,
            "end": 10.0,
            "speaker": "Speaker 1",
            "text": "Hello everyone, welcome to today's meeting about project planning.",
        },
        {
            "start": 10.5,
            "end": 20.0,
            "speaker": "Speaker 2",
            "text": "Thanks for having me. I'm excited to discuss the roadmap.",
        },
        {
            "start": 65.0,
            "end": 75.0,
            "speaker": "Speaker 1",
            "text": "Let's move on to the budget discussion now.",
        },
        {
            "start": 76.0,
            "end": 85.0,
            "speaker": "Speaker 2",
            "text": "The budget looks reasonable for Q1.",
        },
        {
            "start": 140.0,
            "end": 150.0,
            "speaker": "Speaker 1",
            "text": "Now for the final topic, timeline and milestones.",
        },
    ]


@pytest.fixture
def segments_with_topic_changes():
    """Segments with clear topic changes (long gaps)."""
    return [
        {"start": 0.0, "end": 5.0, "speaker": "Speaker 1", "text": "First topic here."},
        {
            "start": 5.5,
            "end": 10.0,
            "speaker": "Speaker 1",
            "text": "Continuing first topic.",
        },
        {
            "start": 15.0,
            "end": 20.0,
            "speaker": "Speaker 2",
            "text": "New topic after gap.",
        },  # 5s gap
        {
            "start": 20.5,
            "end": 25.0,
            "speaker": "Speaker 2",
            "text": "More on second topic.",
        },
    ]


class TestFormatTimestampAnchor:
    """Tests for format_timestamp_anchor function."""

    def test_format_zero(self):
        """Test formatting timestamp at 0 seconds."""
        assert format_timestamp_anchor(0.0) == "[00:00:00]"

    def test_format_seconds_only(self):
        """Test formatting with only seconds."""
        assert format_timestamp_anchor(45.0) == "[00:00:45]"

    def test_format_minutes_seconds(self):
        """Test formatting with minutes and seconds."""
        assert format_timestamp_anchor(125.0) == "[00:02:05]"

    def test_format_hours_minutes_seconds(self):
        """Test formatting with hours, minutes, and seconds."""
        assert format_timestamp_anchor(3665.0) == "[01:01:05]"

    def test_format_rounds_down(self):
        """Test that fractional seconds are rounded down."""
        assert format_timestamp_anchor(45.9) == "[00:00:45]"

    def test_format_large_values(self):
        """Test formatting with large hour values."""
        assert format_timestamp_anchor(36000.0) == "[10:00:00]"


class TestExtractKeyPhrases:
    """Tests for extract_key_phrases function."""

    def test_short_text_unchanged(self):
        """Test that short text is returned unchanged."""
        text = "This is short."
        result = extract_key_phrases(text, max_words=10)
        assert result == "This is short."

    def test_long_text_truncated(self):
        """Test that long text is truncated with ellipsis."""
        text = "This is a very long sentence with many words that should be truncated."
        result = extract_key_phrases(text, max_words=5)
        assert result == "This is a very long..."
        assert result.endswith("...")

    def test_exact_max_words(self):
        """Test text exactly at max words."""
        text = "One two three four five"
        result = extract_key_phrases(text, max_words=5)
        assert result == "One two three four five"
        assert not result.endswith("...")

    def test_custom_max_words(self):
        """Test with custom max_words parameter."""
        text = "Word one word two word three word four word five word six"
        result = extract_key_phrases(text, max_words=3)
        assert result == "Word one word..."

    def test_strips_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        text = "  This has spaces  "
        result = extract_key_phrases(text, max_words=10)
        assert result == "This has spaces"


class TestDetectTopicChange:
    """Tests for detect_topic_change function."""

    def test_first_segment_is_change(self):
        """Test that first segment (no previous) is always a topic change."""
        segment = {"start": 0.0, "end": 5.0, "speaker": "Speaker 1", "text": "Hello."}
        assert detect_topic_change(None, segment) is True

    def test_speaker_change_with_gap(self):
        """Test speaker change with significant gap."""
        prev = {"start": 0.0, "end": 5.0, "speaker": "Speaker 1", "text": "First."}
        curr = {
            "start": 10.0,
            "end": 15.0,
            "speaker": "Speaker 2",
            "text": "Second.",
        }  # 5s gap
        assert detect_topic_change(prev, curr, gap_threshold=3.0) is True

    def test_speaker_change_no_gap(self):
        """Test speaker change without significant gap."""
        prev = {"start": 0.0, "end": 5.0, "speaker": "Speaker 1", "text": "First."}
        curr = {
            "start": 5.5,
            "end": 10.0,
            "speaker": "Speaker 2",
            "text": "Second.",
        }  # 0.5s gap
        assert detect_topic_change(prev, curr, gap_threshold=3.0) is False

    def test_same_speaker_large_gap(self):
        """Test same speaker with very large gap."""
        prev = {"start": 0.0, "end": 5.0, "speaker": "Speaker 1", "text": "First."}
        curr = {
            "start": 20.0,
            "end": 25.0,
            "speaker": "Speaker 1",
            "text": "Second.",
        }  # 15s gap
        # Threshold is 3.0, so 2x threshold is 6.0 - 15s gap should trigger
        assert detect_topic_change(prev, curr, gap_threshold=3.0) is True

    def test_same_speaker_small_gap(self):
        """Test same speaker with small gap."""
        prev = {"start": 0.0, "end": 5.0, "speaker": "Speaker 1", "text": "First."}
        curr = {
            "start": 6.0,
            "end": 10.0,
            "speaker": "Speaker 1",
            "text": "Second.",
        }  # 1s gap
        assert detect_topic_change(prev, curr, gap_threshold=3.0) is False

    def test_custom_threshold(self):
        """Test with custom gap threshold."""
        prev = {"start": 0.0, "end": 5.0, "speaker": "Speaker 1", "text": "First."}
        curr = {
            "start": 10.0,
            "end": 15.0,
            "speaker": "Speaker 2",
            "text": "Second.",
        }  # 5s gap
        assert detect_topic_change(prev, curr, gap_threshold=10.0) is False
        assert detect_topic_change(prev, curr, gap_threshold=2.0) is True


class TestGenerateOutline:
    """Tests for generate_outline function."""

    def test_generate_basic_outline(self, sample_segments):
        """Test basic outline generation."""
        outline = generate_outline(sample_segments, interval_seconds=60.0)

        # Should have multiple entries based on time intervals
        assert len(outline) > 0
        assert all("timestamp" in entry for entry in outline)
        assert all("timestamp_formatted" in entry for entry in outline)
        assert all("speaker" in entry for entry in outline)
        assert all("summary" in entry for entry in outline)

    def test_outline_time_intervals(self, sample_segments):
        """Test that outline respects time intervals."""
        outline = generate_outline(sample_segments, interval_seconds=60.0)

        # With 60s intervals and segments at 0, 10, 65, 76, 140 seconds
        # Should have entries around 0s, 65s, 140s
        assert len(outline) >= 2

    def test_outline_auto_detect_topics(self, segments_with_topic_changes):
        """Test automatic topic change detection."""
        outline = generate_outline(
            segments_with_topic_changes,
            interval_seconds=None,  # Only auto-detect
            auto_detect_topics=True,
            gap_threshold=3.0,
        )

        # Should detect topic change at the 5s gap between segments
        assert len(outline) >= 2

    def test_outline_no_auto_detect(self, segments_with_topic_changes):
        """Test with auto-detect disabled."""
        outline = generate_outline(
            segments_with_topic_changes,
            interval_seconds=100.0,  # Large interval
            auto_detect_topics=False,
        )

        # Without auto-detect and large interval, should have minimal entries
        assert len(outline) >= 1

    def test_outline_empty_segments(self):
        """Test with empty segment list."""
        outline = generate_outline([])
        assert outline == []

    def test_outline_timestamp_format(self, sample_segments):
        """Test that timestamps are properly formatted."""
        outline = generate_outline(sample_segments, interval_seconds=60.0)

        for entry in outline:
            ts = entry["timestamp_formatted"]
            assert ts.startswith("[")
            assert ts.endswith("]")
            assert ":" in ts

    def test_outline_summary_truncation(self, sample_segments):
        """Test that summaries are truncated appropriately."""
        outline = generate_outline(
            sample_segments, interval_seconds=60.0, max_summary_words=5
        )

        # Check that long summaries are truncated
        for entry in outline:
            word_count = len(entry["summary"].replace("...", "").split())
            # Should be <= max_words (accounting for ellipsis)
            assert word_count <= 6  # 5 + possible ellipsis

    def test_outline_preserves_speaker_info(self, sample_segments):
        """Test that speaker information is preserved."""
        outline = generate_outline(sample_segments, interval_seconds=60.0)

        assert all("speaker" in entry for entry in outline)
        # First entry should be from Speaker 1
        assert outline[0]["speaker"] == "Speaker 1"


class TestFormatOutlineMarkdown:
    """Tests for format_outline_markdown function."""

    def test_format_basic_markdown(self):
        """Test basic Markdown formatting."""
        entries = [
            {
                "timestamp_formatted": "[00:00:00]",
                "speaker": "Speaker 1",
                "summary": "Introduction to the meeting",
            },
            {
                "timestamp_formatted": "[00:01:00]",
                "speaker": "Speaker 2",
                "summary": "Discussion of project goals",
            },
        ]
        markdown = format_outline_markdown(entries, title="Test Outline")

        assert "# Test Outline" in markdown
        assert "## [00:00:00] Speaker 1" in markdown
        assert "Introduction to the meeting" in markdown
        assert "## [00:01:00] Speaker 2" in markdown
        assert "Discussion of project goals" in markdown

    def test_format_custom_title(self):
        """Test with custom title."""
        entries = [
            {
                "timestamp_formatted": "[00:00:00]",
                "speaker": "Speaker 1",
                "summary": "Test",
            },
        ]
        markdown = format_outline_markdown(entries, title="My Custom Title")

        assert "# My Custom Title" in markdown

    def test_format_empty_outline(self):
        """Test formatting empty outline."""
        markdown = format_outline_markdown([], title="Empty Outline")

        assert "# Empty Outline" in markdown
        # Should only have title and blank line
        assert len(markdown.split("\n")) <= 3

    def test_format_preserves_order(self):
        """Test that entry order is preserved."""
        entries = [
            {"timestamp_formatted": "[00:00:00]", "speaker": "A", "summary": "First"},
            {"timestamp_formatted": "[00:01:00]", "speaker": "B", "summary": "Second"},
            {"timestamp_formatted": "[00:02:00]", "speaker": "C", "summary": "Third"},
        ]
        markdown = format_outline_markdown(entries)

        # Check that entries appear in order
        first_pos = markdown.find("First")
        second_pos = markdown.find("Second")
        third_pos = markdown.find("Third")

        assert first_pos < second_pos < third_pos

    def test_format_markdown_structure(self):
        """Test proper Markdown heading structure."""
        entries = [
            {
                "timestamp_formatted": "[00:00:00]",
                "speaker": "Speaker 1",
                "summary": "Test",
            },
        ]
        markdown = format_outline_markdown(entries, title="Outline")

        lines = markdown.split("\n")

        # Should have H1 for title
        assert lines[0].startswith("# ")

        # Should have H2 for entries
        assert any(line.startswith("## ") for line in lines)
