"""
Unit tests for plan_from_transcript.py

Tests the PlanGenerator class and LLM-based plan extraction.
"""

import json
import pytest
from pathlib import Path
import sys
from unittest.mock import Mock, patch, MagicMock

# Add pipeline directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.plan_from_transcript import PlanGenerator, PLAN_TEMPLATE


class TestPlanGenerator:
    """Test PlanGenerator class."""

    @pytest.fixture
    def sample_segments(self):
        """Sample transcript segments for testing."""
        return [
            {
                "text": "We have a problem with user authentication",
                "start": 15,
                "speaker": "Alice",
            },
            {
                "text": "Our main users are developers and product managers",
                "start": 90,
                "speaker": "Bob",
            },
            {
                "text": "The goal is to reduce login time by 50%",
                "start": 165,
                "speaker": "Alice",
            },
        ]

    @pytest.fixture
    def sample_segments_file(self, tmp_path, sample_segments):
        """Create a temporary segments JSON file."""
        file_path = tmp_path / "segments.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(sample_segments, f)
        return file_path

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM response with structured plan data."""
        return {
            "problem": (
                "User authentication is slow and causes friction in "
                "the login process."
            ),
            "users": (
                "Developers and product managers who need quick "
                "access to the system."
            ),
            "goals": "- Reduce login time by 50%\n- Improve user satisfaction",
            "acceptance_criteria": (
                "- Login completes in under 2 seconds\n"
                "- No breaking changes to existing integrations"
            ),
            "risks": (
                "- Risk of breaking existing integrations\n"
                "- Performance issues under load"
            ),
            "notes": (
                "Implementation requires careful testing of "
                "authentication flow."
            ),
        }

    @patch("pipeline.plan_from_transcript.anthropic")
    def test_init_claude(self, mock_anthropic):
        """Test PlanGenerator initialization with Claude."""
        mock_client = Mock()
        mock_anthropic.Anthropic.return_value = mock_client

        generator = PlanGenerator(model_type="claude")

        assert generator.model_type == "claude"
        assert generator.client == mock_client
        assert generator.model == "claude-3-5-sonnet-20241022"
        mock_anthropic.Anthropic.assert_called_once()

    @patch("pipeline.plan_from_transcript.openai")
    def test_init_gpt(self, mock_openai):
        """Test PlanGenerator initialization with GPT."""
        mock_client = Mock()
        mock_openai.OpenAI.return_value = mock_client

        generator = PlanGenerator(model_type="gpt")

        assert generator.model_type == "gpt"
        assert generator.client == mock_client
        assert generator.model == "gpt-4o"
        mock_openai.OpenAI.assert_called_once()

    def test_init_invalid_model(self):
        """Test PlanGenerator initialization with invalid model type."""
        with pytest.raises(ValueError, match="Unsupported model_type"):
            PlanGenerator(model_type="invalid")

    @patch("pipeline.plan_from_transcript.ANTHROPIC_AVAILABLE", False)
    def test_init_claude_not_available(self):
        """Test error when Claude package not installed."""
        with pytest.raises(ImportError, match="anthropic package not installed"):
            PlanGenerator(model_type="claude")

    def test_load_segments_list(self, sample_segments_file, sample_segments):
        """Test loading segments from JSON array."""
        with patch("pipeline.plan_from_transcript.anthropic"):
            generator = PlanGenerator(model_type="claude")
            loaded = generator.load_segments(sample_segments_file)
            assert loaded == sample_segments

    def test_load_segments_object(self, tmp_path, sample_segments):
        """Test loading segments from JSON object with 'segments' key."""
        data = {"segments": sample_segments, "metadata": {"duration": 120}}
        file_path = tmp_path / "segments.json"
        with open(file_path, "w") as f:
            json.dump(data, f)

        with patch("pipeline.plan_from_transcript.anthropic"):
            generator = PlanGenerator(model_type="claude")
            loaded = generator.load_segments(file_path)
            assert loaded == sample_segments

    def test_load_segments_invalid_format(self, tmp_path):
        """Test error handling for invalid segment format."""
        file_path = tmp_path / "invalid.json"
        with open(file_path, "w") as f:
            json.dump({"data": "wrong format"}, f)

        with patch("pipeline.plan_from_transcript.anthropic"):
            generator = PlanGenerator(model_type="claude")
            with pytest.raises(ValueError, match="Invalid segments format"):
                generator.load_segments(file_path)

    def test_segments_to_text(self, sample_segments):
        """Test converting segments to plain text transcript."""
        with patch("pipeline.plan_from_transcript.anthropic"):
            generator = PlanGenerator(model_type="claude")
            text = generator.segments_to_text(sample_segments)

            assert "[00:15] Alice: We have a problem with user authentication" in text
            assert (
                "[01:30] Bob: Our main users are developers and product managers"
                in text
            )
            assert "[02:45] Alice: The goal is to reduce login time by 50%" in text

    @patch("pipeline.plan_from_transcript.anthropic")
    def test_extract_plan_data_claude(self, mock_anthropic, mock_llm_response):
        """Test extracting plan data using Claude."""
        # Mock Claude API response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps(mock_llm_response))]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        generator = PlanGenerator(model_type="claude")
        result = generator.extract_plan_data("Sample transcript")

        assert result["problem"] == mock_llm_response["problem"]
        assert result["users"] == mock_llm_response["users"]
        assert result["goals"] == mock_llm_response["goals"]
        mock_client.messages.create.assert_called_once()

    @patch("pipeline.plan_from_transcript.openai")
    def test_extract_plan_data_gpt(self, mock_openai, mock_llm_response):
        """Test extracting plan data using GPT."""
        # Mock OpenAI API response
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content=json.dumps(mock_llm_response)))
        ]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.OpenAI.return_value = mock_client

        generator = PlanGenerator(model_type="gpt")
        result = generator.extract_plan_data("Sample transcript")

        assert result["problem"] == mock_llm_response["problem"]
        assert result["users"] == mock_llm_response["users"]
        mock_client.chat.completions.create.assert_called_once()

    @patch("pipeline.plan_from_transcript.anthropic")
    def test_generate_plan(
        self, mock_anthropic, sample_segments_file, mock_llm_response, tmp_path
    ):
        """Test complete plan generation workflow."""
        # Mock Claude API
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text=json.dumps(mock_llm_response))]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        output_path = tmp_path / "plan.md"
        generator = PlanGenerator(model_type="claude")
        plan_md = generator.generate_plan(
            segments_path=sample_segments_file,
            output_path=output_path,
            title="Test Project Plan",
        )

        # Check plan structure
        assert "# Test Project Plan" in plan_md
        assert "## Problem Statement" in plan_md
        assert "## Target Users" in plan_md
        assert mock_llm_response["problem"] in plan_md
        assert mock_llm_response["users"] in plan_md

        # Check file was saved
        assert output_path.exists()
        assert output_path.read_text() == plan_md


class TestPlanTemplate:
    """Test plan template and formatting."""

    def test_plan_template_has_required_sections(self):
        """Test that PLAN_TEMPLATE includes all required sections."""
        assert "# {title}" in PLAN_TEMPLATE
        assert "## Problem Statement" in PLAN_TEMPLATE
        assert "## Target Users" in PLAN_TEMPLATE
        assert "## Goals & Objectives" in PLAN_TEMPLATE
        assert "## Acceptance Criteria" in PLAN_TEMPLATE
        assert "## Risks & Assumptions" in PLAN_TEMPLATE
        assert "## Additional Notes" in PLAN_TEMPLATE

    def test_plan_template_formatting(self):
        """Test that plan template can be formatted correctly."""
        formatted = PLAN_TEMPLATE.format(
            title="Test Plan",
            date="2025-10-17",
            source="segments.json",
            problem="Test problem",
            users="Test users",
            goals="Test goals",
            acceptance_criteria="Test criteria",
            risks="Test risks",
            notes="Test notes",
        )

        assert "# Test Plan" in formatted
        assert "Test problem" in formatted
        assert "Test users" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
