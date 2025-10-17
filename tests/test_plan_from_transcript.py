"""
Tests for plan_from_transcript.py module.
"""

import json
import pytest
from pathlib import Path
from pipeline.plan_from_transcript import (
    PlanExtractor,
    Plan,
    PlanSection
)


@pytest.fixture
def sample_segments_file(tmp_path):
    """Create sample segments JSON file for testing."""
    segments = [
        {
            "start": 0.0,
            "end": 5.0,
            "text": "We have a problem with users not understanding the onboarding flow."
        },
        {
            "start": 5.5,
            "end": 12.0,
            "text": "Our target users are small business owners who need simple invoicing."
        },
        {
            "start": 12.5,
            "end": 20.0,
            "text": "The goal is to achieve 80% completion rate for new user onboarding."
        },
        {
            "start": 20.5,
            "end": 28.0,
            "text": "Acceptance criteria: Users must complete profile setup within 5 minutes."
        },
        {
            "start": 28.5,
            "end": 35.0,
            "text": "Main risk is that users might abandon if we ask for too much information."
        }
    ]

    segments_file = tmp_path / "test_segments.json"
    with open(segments_file, 'w') as f:
        json.dump(segments, f)

    return segments_file


@pytest.fixture
def sample_segments_with_dict_format(tmp_path):
    """Create segments file with dictionary wrapper format."""
    data = {
        "segments": [
            {
                "start": 0.0,
                "end": 5.0,
                "text": "The main issue is slow page load times affecting user experience."
            }
        ]
    }

    segments_file = tmp_path / "test_segments_dict.json"
    with open(segments_file, 'w') as f:
        json.dump(data, f)

    return segments_file


class TestPlanExtractor:
    """Test PlanExtractor class."""

    def test_load_segments_list_format(self, sample_segments_file):
        """Test loading segments from list format."""
        extractor = PlanExtractor(sample_segments_file)
        assert len(extractor.segments) == 5
        assert extractor.segments[0]['text'].startswith("We have a problem")

    def test_load_segments_dict_format(self, sample_segments_with_dict_format):
        """Test loading segments from dictionary format."""
        extractor = PlanExtractor(sample_segments_with_dict_format)
        assert len(extractor.segments) == 1
        assert "issue" in extractor.segments[0]['text']

    def test_extract_timestamp(self, sample_segments_file):
        """Test timestamp extraction from segments."""
        extractor = PlanExtractor(sample_segments_file)
        timestamp = extractor._extract_timestamp({"start": 125.5})
        assert timestamp == "02:05"

        timestamp = extractor._extract_timestamp({"start": 45.0})
        assert timestamp == "00:45"

    def test_get_segment_text(self, sample_segments_file):
        """Test text extraction from segments."""
        extractor = PlanExtractor(sample_segments_file)

        # Test 'text' field
        text = extractor._get_segment_text({"text": "  Some text  "})
        assert text == "Some text"

        # Test 'content' field
        text = extractor._get_segment_text({"content": "  Other text  "})
        assert text == "Other text"

        # Test empty segment
        text = extractor._get_segment_text({})
        assert text == ""

    def test_classify_segment(self, sample_segments_file):
        """Test segment classification based on keywords."""
        extractor = PlanExtractor(sample_segments_file)

        # Test problem classification
        sections = extractor._classify_segment("We have a problem with the UI")
        assert "problem_statement" in sections

        # Test user classification
        sections = extractor._classify_segment("Our users need better tools")
        assert "target_users" in sections

        # Test goal classification
        sections = extractor._classify_segment("The objective is to improve performance")
        assert "goals_objectives" in sections

        # Test acceptance criteria
        sections = extractor._classify_segment("Requirements include login functionality")
        assert "acceptance_criteria" in sections

        # Test risk classification
        sections = extractor._classify_segment("There is a risk of data loss")
        assert "risks_considerations" in sections

        # Test multiple classifications
        sections = extractor._classify_segment("The goal is to solve the user problem")
        assert "goals_objectives" in sections
        assert "problem_statement" in sections
        assert "target_users" in sections

    def test_extract_plan(self, sample_segments_file):
        """Test full plan extraction."""
        extractor = PlanExtractor(sample_segments_file)
        plan = extractor.extract_plan(title="Test Plan")

        assert plan.title == "Test Plan"
        assert plan.source_file == str(sample_segments_file)
        assert len(plan.sections) > 0

        # Check specific sections were created
        assert "problem_statement" in plan.sections
        assert "target_users" in plan.sections
        assert "goals_objectives" in plan.sections
        assert "acceptance_criteria" in plan.sections
        assert "risks_considerations" in plan.sections

        # Verify section content
        assert len(plan.sections["problem_statement"].content) > 0
        assert len(plan.sections["problem_statement"].timestamps) > 0

    def test_extract_plan_default_title(self, sample_segments_file):
        """Test plan extraction with default title."""
        extractor = PlanExtractor(sample_segments_file)
        plan = extractor.extract_plan()

        assert "test_segments" in plan.title

    def test_save_plan_markdown(self, sample_segments_file, tmp_path):
        """Test saving plan as markdown."""
        extractor = PlanExtractor(sample_segments_file)
        plan = extractor.extract_plan(title="Markdown Test Plan")

        output_file = tmp_path / "test_plan.md"
        extractor.save_plan(plan, output_file, format="markdown")

        assert output_file.exists()
        content = output_file.read_text()

        # Verify markdown structure
        assert "# Markdown Test Plan" in content
        assert "## Problem Statement" in content
        assert "## Target Users" in content
        assert "Generated:" in content
        assert "Source:" in content

    def test_save_plan_json(self, sample_segments_file, tmp_path):
        """Test saving plan as JSON."""
        extractor = PlanExtractor(sample_segments_file)
        plan = extractor.extract_plan(title="JSON Test Plan")

        output_file = tmp_path / "test_plan.json"
        extractor.save_plan(plan, output_file, format="json")

        assert output_file.exists()

        # Verify JSON structure
        with open(output_file, 'r') as f:
            data = json.load(f)

        assert data['title'] == "JSON Test Plan"
        assert 'sections' in data
        assert 'generated_date' in data


class TestPlan:
    """Test Plan dataclass."""

    def test_plan_to_markdown(self):
        """Test Plan markdown conversion."""
        sections = {
            "problem_statement": PlanSection(
                title="Problem Statement",
                content=["Issue 1", "Issue 2"],
                timestamps=["00:00", "00:10"]
            ),
            "target_users": PlanSection(
                title="Target Users",
                content=["User type 1"],
                timestamps=["00:20"]
            )
        }

        plan = Plan(
            title="Test Plan",
            generated_date="2025-01-01 12:00:00",
            source_file="test.json",
            sections=sections
        )

        markdown = plan.to_markdown()

        # Verify structure
        assert "# Test Plan" in markdown
        assert "## Problem Statement" in markdown
        assert "- Issue 1" in markdown
        assert "- Issue 2" in markdown
        assert "00:00, 00:10" in markdown
        assert "## Target Users" in markdown
        assert "- User type 1" in markdown

    def test_plan_empty_sections(self):
        """Test Plan with no sections."""
        plan = Plan(
            title="Empty Plan",
            generated_date="2025-01-01",
            source_file="empty.json",
            sections={}
        )

        markdown = plan.to_markdown()
        assert "# Empty Plan" in markdown
        assert "Generated:" in markdown


class TestPlanSection:
    """Test PlanSection dataclass."""

    def test_plan_section_creation(self):
        """Test creating PlanSection."""
        section = PlanSection(
            title="Test Section",
            content=["Item 1", "Item 2"],
            timestamps=["00:00", "01:00"]
        )

        assert section.title == "Test Section"
        assert len(section.content) == 2
        assert len(section.timestamps) == 2


def test_integration_full_pipeline(tmp_path):
    """Integration test for complete pipeline."""
    # Create comprehensive test segments
    segments = [
        {"start": 0, "text": "The problem is users cannot find the settings page easily"},
        {"start": 10, "text": "Our target audience includes enterprise customers and SMBs"},
        {"start": 20, "text": "The main goal is to improve navigation clarity by 50%"},
        {"start": 30, "text": "Acceptance criteria: Settings must be accessible within 2 clicks"},
        {"start": 40, "text": "Risk: Changes might confuse existing power users"},
        {"start": 50, "text": "Another issue is the search functionality being slow"},
        {"start": 60, "text": "We aim to achieve sub-second search results"},
    ]

    segments_file = tmp_path / "integration_test.json"
    with open(segments_file, 'w') as f:
        json.dump(segments, f)

    # Extract plan
    extractor = PlanExtractor(segments_file)
    plan = extractor.extract_plan(title="Integration Test Plan")

    # Verify extraction
    assert plan.title == "Integration Test Plan"
    assert len(plan.sections) >= 3

    # Save both formats
    md_file = tmp_path / "plan.md"
    json_file = tmp_path / "plan.json"

    extractor.save_plan(plan, md_file, format="markdown")
    extractor.save_plan(plan, json_file, format="json")

    assert md_file.exists()
    assert json_file.exists()

    # Verify markdown output
    md_content = md_file.read_text()
    assert "Integration Test Plan" in md_content
    assert "Problem Statement" in md_content
    assert "Goals & Objectives" in md_content

    # Verify JSON output
    with open(json_file, 'r') as f:
        json_data = json.load(f)
    assert json_data['title'] == "Integration Test Plan"
