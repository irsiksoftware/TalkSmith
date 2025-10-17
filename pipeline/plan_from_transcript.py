"""
Generate structured PRD/plan documents from transcript segments using LLM.

This module extracts key sections from meeting transcripts:
- Problem Statement
- Target Users
- Goals & Objectives
- Acceptance Criteria
- Risks & Assumptions

Usage:
    python -m pipeline.plan_from_transcript --input segments.json --output plan.md
    python -m pipeline.plan_from_transcript --input segments.json --google-docs
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


PLAN_TEMPLATE = """# {title}

**Date:** {date}
**Source:** {source}

## Problem Statement
{problem}

## Target Users
{users}

## Goals & Objectives
{goals}

## Acceptance Criteria
{acceptance_criteria}

## Risks & Assumptions
{risks}

## Additional Notes
{notes}
"""


EXTRACTION_PROMPT = """You are analyzing a meeting or interview transcript to extract structured information for a Product Requirements Document (PRD) or project plan.

Review the following transcript and extract:

1. **Problem Statement**: What problem is being solved? What pain points are mentioned?
2. **Target Users**: Who will use this? What are their characteristics?
3. **Goals & Objectives**: What are the desired outcomes? What success metrics are mentioned?
4. **Acceptance Criteria**: What conditions must be met? What defines "done"?
5. **Risks & Assumptions**: What challenges, dependencies, or assumptions are mentioned?
6. **Additional Notes**: Any other important context, decisions, or action items.

Transcript:
{transcript}

Respond in JSON format with these exact keys:
{{
  "problem": "string",
  "users": "string",
  "goals": "string",
  "acceptance_criteria": "string",
  "risks": "string",
  "notes": "string"
}}

Be concise but comprehensive. Use bullet points where appropriate. If a section has no clear information, write "Not specified in transcript."
"""


class PlanGenerator:
    """Generate structured plans from transcripts using LLM."""

    def __init__(self, model_type: str = "claude", api_key: Optional[str] = None):
        """
        Initialize the plan generator.

        Args:
            model_type: Either "claude" or "gpt" (default: "claude")
            api_key: API key for the chosen model. If None, reads from environment.
        """
        self.model_type = model_type.lower()

        if self.model_type == "claude":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError(
                    "anthropic package not installed. Run: pip install anthropic"
                )
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = "claude-3-5-sonnet-20241022"
        elif self.model_type == "gpt":
            if not OPENAI_AVAILABLE:
                raise ImportError(
                    "openai package not installed. Run: pip install openai"
                )
            self.client = openai.OpenAI(api_key=api_key)
            self.model = "gpt-4o"
        else:
            raise ValueError(
                f"Unsupported model_type: {model_type}. Use 'claude' or 'gpt'."
            )

    def load_segments(self, segments_path: Path) -> List[Dict]:
        """Load transcript segments from JSON file."""
        logger.info(f"Loading segments from {segments_path}")
        with open(segments_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Handle different segment formats
        if isinstance(data, list):
            segments = data
        elif isinstance(data, dict) and "segments" in data:
            segments = data["segments"]
        else:
            raise ValueError(
                "Invalid segments format. Expected list or dict with 'segments' key."
            )

        logger.info(f"Loaded {len(segments)} segments")
        return segments

    def segments_to_text(self, segments: List[Dict]) -> str:
        """Convert segments to plain text transcript."""
        lines = []
        for seg in segments:
            timestamp = seg.get("start", 0)
            text = seg.get("text", "").strip()
            speaker = seg.get("speaker", "Unknown")

            # Format: [00:00] Speaker: Text
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            lines.append(f"[{minutes:02d}:{seconds:02d}] {speaker}: {text}")

        return "\n".join(lines)

    def extract_plan_data(self, transcript: str) -> Dict[str, str]:
        """
        Extract structured plan data from transcript using LLM.

        Args:
            transcript: Plain text transcript

        Returns:
            Dict with keys: problem, users, goals, acceptance_criteria, risks, notes
        """
        logger.info(f"Extracting plan data using {self.model_type}")

        prompt = EXTRACTION_PROMPT.format(transcript=transcript)

        if self.model_type == "claude":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text
        else:  # gpt
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content

        # Parse JSON response
        try:
            plan_data = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re

            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                plan_data = json.loads(json_match.group(1))
            else:
                raise ValueError(f"Failed to parse LLM response as JSON: {content}")

        # Validate required keys
        required_keys = [
            "problem",
            "users",
            "goals",
            "acceptance_criteria",
            "risks",
            "notes",
        ]
        for key in required_keys:
            if key not in plan_data:
                plan_data[key] = "Not specified in transcript."

        logger.info("Successfully extracted plan data")
        return plan_data

    def generate_plan(
        self,
        segments_path: Path,
        output_path: Optional[Path] = None,
        title: Optional[str] = None,
    ) -> str:
        """
        Generate a structured plan document from transcript segments.

        Args:
            segments_path: Path to segments JSON file
            output_path: Optional path to save plan markdown file
            title: Optional title for the plan (default: filename)

        Returns:
            Generated plan as markdown string
        """
        # Load and convert segments
        segments = self.load_segments(segments_path)
        transcript = self.segments_to_text(segments)

        # Extract structured data
        plan_data = self.extract_plan_data(transcript)

        # Generate plan document
        if title is None:
            title = segments_path.stem.replace("_", " ").title()

        plan_md = PLAN_TEMPLATE.format(
            title=title,
            date=datetime.now().strftime("%Y-%m-%d"),
            source=segments_path.name,
            problem=plan_data["problem"],
            users=plan_data["users"],
            goals=plan_data["goals"],
            acceptance_criteria=plan_data["acceptance_criteria"],
            risks=plan_data["risks"],
            notes=plan_data["notes"],
        )

        # Save to file if requested
        if output_path:
            logger.info(f"Saving plan to {output_path}")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(plan_md)

        return plan_md


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate structured PRD/plan from transcript segments"
    )
    parser.add_argument(
        "--input", "-i", type=Path, required=True, help="Input segments JSON file"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output plan markdown file (default: input_name_plan.md)",
    )
    parser.add_argument(
        "--title", "-t", type=str, help="Plan title (default: derived from filename)"
    )
    parser.add_argument(
        "--model",
        type=str,
        choices=["claude", "gpt"],
        default="claude",
        help="LLM model to use (default: claude)",
    )
    parser.add_argument(
        "--google-docs", action="store_true", help="Upload plan to Google Docs"
    )
    parser.add_argument(
        "--google-docs-title",
        type=str,
        help="Google Docs document title (default: same as plan title)",
    )

    args = parser.parse_args()

    # Validate input
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return 1

    # Set default output path
    if args.output is None:
        args.output = args.input.parent / f"{args.input.stem}_plan.md"

    # Generate plan
    try:
        generator = PlanGenerator(model_type=args.model)
        plan_md = generator.generate_plan(
            segments_path=args.input, output_path=args.output, title=args.title
        )

        logger.info(f"Plan generated successfully: {args.output}")

        # Upload to Google Docs if requested
        if args.google_docs:
            try:
                from pipeline.google_docs_integration import GoogleDocsUploader

                uploader = GoogleDocsUploader()
                doc_title = args.google_docs_title or args.title or args.input.stem
                doc_url = uploader.create_document_from_markdown(plan_md, doc_title)

                logger.info(f"Plan uploaded to Google Docs: {doc_url}")
                print(f"\nGoogle Docs URL: {doc_url}")

            except ImportError:
                logger.error(
                    "Google Docs integration not available. Check google_docs_integration.py"
                )
                return 1
            except Exception as e:
                logger.error(f"Failed to upload to Google Docs: {e}")
                return 1

        print(f"\nPlan saved to: {args.output}")
        return 0

    except Exception as e:
        logger.error(f"Failed to generate plan: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
