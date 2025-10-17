#!/usr/bin/env python3
"""
Extract structured PRD/plan from transcription segments.

Transforms conversation segments into actionable documents with sections:
- Problem Statement
- Target Users
- Goals & Objectives
- Acceptance Criteria
- Risks & Considerations
"""

import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class PlanSection:
    """Represents a section in the plan document."""
    title: str
    content: List[str]
    timestamps: List[str]


@dataclass
class Plan:
    """Structured plan document."""
    title: str
    generated_date: str
    source_file: str
    sections: Dict[str, PlanSection]

    def to_markdown(self) -> str:
        """Convert plan to markdown format."""
        lines = [
            f"# {self.title}",
            "",
            f"**Generated:** {self.generated_date}  ",
            f"**Source:** {self.source_file}",
            "",
            "---",
            ""
        ]

        section_order = [
            "problem_statement",
            "target_users",
            "goals_objectives",
            "acceptance_criteria",
            "risks_considerations"
        ]

        for section_key in section_order:
            if section_key in self.sections:
                section = self.sections[section_key]
                lines.append(f"## {section.title}")
                lines.append("")

                for item in section.content:
                    lines.append(f"- {item}")

                if section.timestamps:
                    lines.append("")
                    lines.append(f"*Referenced timestamps: {', '.join(section.timestamps)}*")

                lines.append("")

        return "\n".join(lines)


class PlanExtractor:
    """Extract structured plan from transcript segments."""

    SECTION_KEYWORDS = {
        "problem_statement": ["problem", "issue", "challenge", "pain point", "difficulty"],
        "target_users": ["user", "customer", "client", "audience", "stakeholder"],
        "goals_objectives": ["goal", "objective", "aim", "target", "outcome", "achieve"],
        "acceptance_criteria": ["criteria", "requirement", "must have", "should", "acceptance"],
        "risks_considerations": ["risk", "concern", "challenge", "limitation", "consideration"]
    }

    SECTION_TITLES = {
        "problem_statement": "Problem Statement",
        "target_users": "Target Users",
        "goals_objectives": "Goals & Objectives",
        "acceptance_criteria": "Acceptance Criteria",
        "risks_considerations": "Risks & Considerations"
    }

    def __init__(self, segments_file: Path):
        """Initialize extractor with segments file."""
        self.segments_file = segments_file
        self.segments = self._load_segments()

    def _load_segments(self) -> List[Dict]:
        """Load transcript segments from JSON file."""
        try:
            with open(self.segments_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different segment formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'segments' in data:
                return data['segments']
            else:
                logger.warning(f"Unexpected segment format in {self.segments_file}")
                return []
        except Exception as e:
            logger.error(f"Failed to load segments: {e}")
            raise

    def _extract_timestamp(self, segment: Dict) -> str:
        """Extract timestamp from segment."""
        if 'start' in segment:
            minutes = int(segment['start'] // 60)
            seconds = int(segment['start'] % 60)
            return f"{minutes:02d}:{seconds:02d}"
        return "00:00"

    def _get_segment_text(self, segment: Dict) -> str:
        """Extract text from segment."""
        if 'text' in segment:
            return segment['text'].strip()
        elif 'content' in segment:
            return segment['content'].strip()
        return ""

    def _classify_segment(self, text: str) -> List[str]:
        """Classify segment into one or more sections based on keywords."""
        text_lower = text.lower()
        matched_sections = []

        for section_key, keywords in self.SECTION_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                matched_sections.append(section_key)

        return matched_sections

    def extract_plan(self, title: Optional[str] = None) -> Plan:
        """Extract plan from loaded segments."""
        if title is None:
            title = f"Plan from {self.segments_file.stem}"

        # Initialize sections
        sections = {
            key: PlanSection(
                title=self.SECTION_TITLES[key],
                content=[],
                timestamps=[]
            )
            for key in self.SECTION_KEYWORDS.keys()
        }

        # Process segments
        for segment in self.segments:
            text = self._get_segment_text(segment)
            if not text:
                continue

            timestamp = self._extract_timestamp(segment)
            matched_sections = self._classify_segment(text)

            # Add to matched sections
            for section_key in matched_sections:
                sections[section_key].content.append(text)
                sections[section_key].timestamps.append(timestamp)

        # Remove empty sections
        sections = {k: v for k, v in sections.items() if v.content}

        plan = Plan(
            title=title,
            generated_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            source_file=str(self.segments_file),
            sections=sections
        )

        return plan

    def save_plan(self, plan: Plan, output_file: Path, format: str = "markdown"):
        """Save plan to file."""
        if format == "markdown":
            content = plan.to_markdown()
            output_file.write_text(content, encoding='utf-8')
            logger.info(f"Saved plan to {output_file}")
        elif format == "json":
            # Convert to JSON-serializable format
            plan_dict = asdict(plan)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(plan_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved plan to {output_file}")
        else:
            raise ValueError(f"Unsupported format: {format}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract structured plan from transcript segments"
    )
    parser.add_argument(
        "segments_file",
        type=Path,
        help="Path to segments JSON file"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path (default: plan.md in same directory)"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "-t", "--title",
        type=str,
        help="Plan title (default: auto-generated from filename)"
    )
    parser.add_argument(
        "--google-docs",
        action="store_true",
        help="Push plan to Google Docs after generation"
    )

    args = parser.parse_args()

    # Validate input
    if not args.segments_file.exists():
        logger.error(f"Segments file not found: {args.segments_file}")
        return 1

    # Set output file
    if args.output is None:
        output_ext = ".md" if args.format == "markdown" else ".json"
        args.output = args.segments_file.parent / f"plan{output_ext}"

    # Extract plan
    logger.info(f"Processing segments from {args.segments_file}")
    extractor = PlanExtractor(args.segments_file)
    plan = extractor.extract_plan(title=args.title)

    # Report statistics
    total_items = sum(len(section.content) for section in plan.sections.values())
    logger.info(f"Extracted {len(plan.sections)} sections with {total_items} total items")

    # Save plan
    extractor.save_plan(plan, args.output, format=args.format)

    # Optional: Push to Google Docs
    if args.google_docs:
        try:
            from pipeline.google_docs_integration import GoogleDocsPublisher

            logger.info("Pushing plan to Google Docs...")
            publisher = GoogleDocsPublisher()
            doc_url = publisher.create_document(plan)
            logger.info(f"Plan published to Google Docs: {doc_url}")
        except ImportError:
            logger.error("Google Docs integration not available. Install required dependencies.")
            return 1
        except Exception as e:
            logger.error(f"Failed to push to Google Docs: {e}")
            return 1

    logger.info("Plan generation completed successfully")
    return 0


if __name__ == "__main__":
    exit(main())
