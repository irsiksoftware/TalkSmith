#!/usr/bin/env python3
"""
Example: Generate plan from transcript and publish to Google Docs.

This demonstrates the complete workflow:
1. Load transcript segments
2. Extract structured plan
3. Publish to Google Docs
4. Share with collaborators (optional)

Prerequisites:
    - Google Cloud project with Docs API enabled
    - credentials.json downloaded from Google Cloud Console
    - Install dependencies: pip install -r requirements.txt

Usage:
    # Basic usage - local file only
    python examples/google_docs_example.py

    # Publish to Google Docs
    python examples/google_docs_example.py --publish

    # Publish and share
    python examples/google_docs_example.py --publish --share user@example.com
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from pipeline.plan_from_transcript import PlanGenerator, load_segments, save_markdown
from pipeline.google_docs_integration import GoogleDocsClient


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Example: Generate and publish plan to Google Docs"
    )
    parser.add_argument(
        "--segments",
        type=Path,
        default=Path("examples/sample_segments.json"),
        help="Path to segments file (default: examples/sample_segments.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/example_plan.md"),
        help="Local output file (default: output/example_plan.md)",
    )
    parser.add_argument(
        "--title", default="TalkSmith Example Plan", help="Document title"
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish to Google Docs (requires authentication)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/google_docs.ini"),
        help="Google Docs config file",
    )
    parser.add_argument(
        "--share",
        metavar="EMAIL",
        action="append",
        help="Share with email address (can be used multiple times)",
    )
    parser.add_argument(
        "--role",
        default="writer",
        choices=["reader", "writer", "commenter"],
        help="Sharing role (default: writer)",
    )

    args = parser.parse_args()

    # Validate input
    if not args.segments.exists():
        print(f"ERROR: Segments file not found: {args.segments}")
        print("Try using the default: examples/sample_segments.json")
        sys.exit(1)

    print("=" * 60)
    print("TalkSmith Google Docs Integration Example")
    print("=" * 60)
    print()

    # Step 1: Load segments
    print(f"[1/4] Loading segments from: {args.segments}")
    segments = load_segments(args.segments)
    print(f"      > Loaded {len(segments)} segments")

    # Step 2: Extract plan structure
    print(f"[2/4] Extracting plan structure...")
    generator = PlanGenerator(segments)
    plan_sections = generator.extract_sections()

    # Count total items across sections
    total_items = sum(len(items) for items in plan_sections.values())
    print(
        f"      > Found {total_items} items across {len([k for k, v in plan_sections.items() if v])} sections"
    )

    # Step 3: Format as markdown
    print(f"[3/4] Formatting markdown...")
    markdown = generator.generate_markdown(title=args.title)

    # Save locally
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_markdown(markdown, args.output)
    print(f"      > Saved to: {args.output}")

    # Step 4: Publish to Google Docs (if requested)
    if args.publish:
        print(f"[4/4] Publishing to Google Docs...")

        if not args.config.exists():
            print(f"      [ERROR]: Config file not found: {args.config}")
            print()
            print("Setup instructions:")
            print("1. Go to https://console.cloud.google.com/")
            print("2. Enable Google Docs API and Google Drive API")
            print("3. Create OAuth 2.0 credentials (Desktop app)")
            print("4. Download credentials.json to config/")
            print("5. Copy config/google_docs.ini.example to config/google_docs.ini")
            print()
            print("See docs/google_docs_setup.md for details")
            sys.exit(1)

        try:
            client = GoogleDocsClient(str(args.config))
            doc_url = client.create_document(args.title, markdown)
            print(f"      > Published: {doc_url}")

            # Extract document ID from URL
            doc_id = doc_url.split("/d/")[1].split("/")[0]

            # Share if requested
            if args.share:
                print(f"      Sharing document...")
                for email in args.share:
                    try:
                        client._share_document(doc_id, email, args.role)
                        print(f"        [OK] Shared with {email} ({args.role})")
                    except Exception as e:
                        print(f"        [FAIL] Failed to share with {email}: {e}")

            print()
            print("=" * 60)
            print("SUCCESS!")
            print("=" * 60)
            print(f"Local file:  {args.output}")
            print(f"Google Docs: {doc_url}")
            print()

        except FileNotFoundError as e:
            print(f"      [ERROR]: {e}")
            print()
            print("See docs/google_docs_setup.md for setup instructions")
            sys.exit(1)

        except Exception as e:
            print(f"      [ERROR]: {e}")
            sys.exit(1)
    else:
        print(f"[4/4] Skipping Google Docs publish (use --publish flag)")
        print()
        print("=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"Local file: {args.output}")
        print()
        print("To publish to Google Docs, run:")
        print(f"  python examples/google_docs_example.py --publish")
        print()

    # Show preview
    print("Preview (first 500 chars):")
    print("-" * 60)
    print(markdown[:500])
    if len(markdown) > 500:
        print("...")
    print("-" * 60)


if __name__ == "__main__":
    main()
