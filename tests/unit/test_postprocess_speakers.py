"""Tests for speaker post-processing functionality."""

import pytest
from pipeline.postprocess_speakers import (
    normalize_speaker_names,
    merge_short_utterances,
    postprocess_speakers,
)


@pytest.fixture
def sample_segments():
    """Sample segments with various speaker patterns."""
    return [
        {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00", "text": "Hello there."},
        {"start": 2.5, "end": 4.0, "speaker": "SPEAKER_01", "text": "Hi!"},
        {"start": 4.5, "end": 7.0, "speaker": "SPEAKER_00", "text": "How are you?"},
        {"start": 7.5, "end": 10.0, "speaker": "SPEAKER_01", "text": "I'm doing well, thanks."},
    ]


@pytest.fixture
def segments_with_short_utterances():
    """Segments with short utterances that should be merged."""
    return [
        {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00", "text": "Hello."},
        {"start": 2.1, "end": 2.5, "speaker": "SPEAKER_00", "text": "Yes."},  # Short, same speaker
        {"start": 2.6, "end": 5.0, "speaker": "SPEAKER_00", "text": "I agree completely."},
        {"start": 6.0, "end": 8.0, "speaker": "SPEAKER_01", "text": "Interesting point."},
    ]


class TestNormalizeSpeakerNames:
    """Tests for normalize_speaker_names function."""

    def test_normalize_basic(self, sample_segments):
        """Test basic speaker name normalization."""
        result = normalize_speaker_names(sample_segments)

        # Check all segments are present
        assert len(result) == len(sample_segments)

        # Check speakers are normalized
        assert result[0]["speaker"] == "Speaker 1"
        assert result[1]["speaker"] == "Speaker 2"
        assert result[2]["speaker"] == "Speaker 1"
        assert result[3]["speaker"] == "Speaker 2"

    def test_normalize_custom_prefix(self, sample_segments):
        """Test normalization with custom prefix."""
        result = normalize_speaker_names(sample_segments, prefix="Person")

        assert result[0]["speaker"] == "Person 1"
        assert result[1]["speaker"] == "Person 2"

    def test_normalize_empty_segments(self):
        """Test with empty segment list."""
        result = normalize_speaker_names([])
        assert result == []

    def test_normalize_preserves_other_fields(self, sample_segments):
        """Test that normalization preserves other segment fields."""
        result = normalize_speaker_names(sample_segments)

        assert result[0]["start"] == sample_segments[0]["start"]
        assert result[0]["end"] == sample_segments[0]["end"]
        assert result[0]["text"] == sample_segments[0]["text"]

    def test_normalize_segments_without_speaker(self):
        """Test normalization with segments missing speaker field."""
        segments = [
            {"start": 0.0, "end": 2.0, "text": "No speaker here."},
            {"start": 2.0, "end": 4.0, "speaker": "SPEAKER_00", "text": "I have a speaker."},
        ]
        result = normalize_speaker_names(segments)

        # Segment without speaker should remain unchanged
        assert "speaker" not in result[0]
        assert result[1]["speaker"] == "Speaker 1"

    def test_normalize_consistent_ordering(self):
        """Test that speaker ordering is consistent."""
        segments = [
            {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_02", "text": "Third."},
            {"start": 2.0, "end": 4.0, "speaker": "SPEAKER_00", "text": "First."},
            {"start": 4.0, "end": 6.0, "speaker": "SPEAKER_01", "text": "Second."},
        ]
        result = normalize_speaker_names(segments)

        # Should be sorted: SPEAKER_00 -> 1, SPEAKER_01 -> 2, SPEAKER_02 -> 3
        assert result[0]["speaker"] == "Speaker 3"  # SPEAKER_02
        assert result[1]["speaker"] == "Speaker 1"  # SPEAKER_00
        assert result[2]["speaker"] == "Speaker 2"  # SPEAKER_01


class TestMergeShortUtterances:
    """Tests for merge_short_utterances function."""

    def test_merge_short_same_speaker(self, segments_with_short_utterances):
        """Test merging short utterances from same speaker."""
        result = merge_short_utterances(segments_with_short_utterances, min_duration_ms=1000)

        # Should merge first 3 segments (all from SPEAKER_00)
        assert len(result) < len(segments_with_short_utterances)

        # First merged segment should contain combined text
        assert "Hello." in result[0]["text"]
        assert "Yes." in result[0]["text"]
        assert "I agree completely." in result[0]["text"]

    def test_merge_preserves_timestamps(self, segments_with_short_utterances):
        """Test that merging preserves start of first and end of last segment."""
        result = merge_short_utterances(segments_with_short_utterances, min_duration_ms=1000)

        # First segment should start at original time
        assert result[0]["start"] == 0.0
        # Should end at the end of third segment
        assert result[0]["end"] == 5.0

    def test_merge_no_merge_needed(self, sample_segments):
        """Test when all utterances are long enough."""
        result = merge_short_utterances(sample_segments, min_duration_ms=1000)

        # All segments are >= 1 second, so length should be similar
        # (might still merge if same speaker and close gap)
        assert len(result) > 0

    def test_merge_empty_segments(self):
        """Test with empty segment list."""
        result = merge_short_utterances([])
        assert result == []

    def test_merge_zero_threshold(self, segments_with_short_utterances):
        """Test with zero threshold (no merging)."""
        result = merge_short_utterances(segments_with_short_utterances, min_duration_ms=0)

        # Should return original segments unchanged
        assert len(result) == len(segments_with_short_utterances)

    def test_merge_different_speakers_not_merged(self):
        """Test that different speakers are not merged."""
        segments = [
            {"start": 0.0, "end": 0.3, "speaker": "SPEAKER_00", "text": "Hi."},
            {"start": 0.4, "end": 0.7, "speaker": "SPEAKER_01", "text": "Hey."},
        ]
        result = merge_short_utterances(segments, min_duration_ms=1000)

        # Should not merge different speakers
        assert len(result) == 2

    def test_merge_with_words_field(self):
        """Test that words field is merged when present."""
        segments = [
            {
                "start": 0.0,
                "end": 0.5,
                "speaker": "SPEAKER_00",
                "text": "Hello.",
                "words": [{"word": "Hello", "start": 0.0, "end": 0.5}],
            },
            {
                "start": 0.6,
                "end": 1.0,
                "speaker": "SPEAKER_00",
                "text": "World.",
                "words": [{"word": "World", "start": 0.6, "end": 1.0}],
            },
        ]
        result = merge_short_utterances(segments, min_duration_ms=1000)

        assert len(result) == 1
        assert "words" in result[0]
        assert len(result[0]["words"]) == 2

    def test_merge_gap_handling(self):
        """Test that segments with large gaps are not merged."""
        segments = [
            {"start": 0.0, "end": 0.5, "speaker": "SPEAKER_00", "text": "First."},
            {"start": 5.0, "end": 5.5, "speaker": "SPEAKER_00", "text": "Second."},  # 4.5s gap
        ]
        result = merge_short_utterances(segments, min_duration_ms=1000)

        # Large gap should prevent merging
        assert len(result) == 2


class TestPostprocessSpeakers:
    """Tests for postprocess_speakers main function."""

    def test_full_postprocessing(self, segments_with_short_utterances):
        """Test full post-processing with normalization and merging."""
        result = postprocess_speakers(
            segments_with_short_utterances,
            normalize_names=True,
            speaker_prefix="Speaker",
            min_utterance_ms=1000,
        )

        # Should have merged segments
        assert len(result) < len(segments_with_short_utterances)

        # Should have normalized names
        assert "Speaker" in result[0]["speaker"]

    def test_normalization_only(self, sample_segments):
        """Test with only normalization enabled."""
        result = postprocess_speakers(
            sample_segments,
            normalize_names=True,
            min_utterance_ms=None,
        )

        # Length should stay the same (no merging)
        assert len(result) == len(sample_segments)

        # Names should be normalized
        assert result[0]["speaker"] == "Speaker 1"

    def test_merging_only(self, segments_with_short_utterances):
        """Test with only merging enabled."""
        result = postprocess_speakers(
            segments_with_short_utterances,
            normalize_names=False,
            min_utterance_ms=1000,
        )

        # Should have merged segments
        assert len(result) < len(segments_with_short_utterances)

        # Names should NOT be normalized
        assert result[0]["speaker"] == "SPEAKER_00"

    def test_no_processing(self, sample_segments):
        """Test with all processing disabled."""
        result = postprocess_speakers(
            sample_segments,
            normalize_names=False,
            min_utterance_ms=None,
        )

        # Should be essentially unchanged
        assert len(result) == len(sample_segments)
        assert result[0]["speaker"] == sample_segments[0]["speaker"]

    def test_custom_speaker_prefix(self, sample_segments):
        """Test with custom speaker prefix."""
        result = postprocess_speakers(
            sample_segments,
            normalize_names=True,
            speaker_prefix="Participant",
            min_utterance_ms=None,
        )

        assert result[0]["speaker"] == "Participant 1"
        assert result[1]["speaker"] == "Participant 2"

    def test_preserves_segment_structure(self, sample_segments):
        """Test that processing preserves essential segment structure."""
        result = postprocess_speakers(sample_segments)

        for segment in result:
            assert "start" in segment
            assert "end" in segment
            assert "text" in segment
            assert isinstance(segment["start"], (int, float))
            assert isinstance(segment["end"], (int, float))
            assert isinstance(segment["text"], str)
