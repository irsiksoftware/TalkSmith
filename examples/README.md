# TalkSmith Examples

This directory contains example scripts and sample data for demonstrating TalkSmith features.

## Files

### Sample Data

**sample_segments.json** - Example transcript segments from a product planning meeting
- Contains 20 segments with timestamps, speakers, and text
- Demonstrates various plan sections: problems, goals, users, acceptance criteria, risks
- Ready to use with plan generation scripts

### Example Scripts

**google_docs_example.py** - Complete workflow demonstration
- Load transcript segments
- Extract structured plan sections
- Generate markdown-formatted plan
- Optionally publish to Google Docs
- Share with collaborators

### Generated Output

**example_plan.md** - Sample markdown plan output
- Shows expected format and structure
- Demonstrates section organization
- Includes timestamps and speaker attribution

**sample_plan_output.md** - Another example output
- Alternative format example
- Reference for expected results

## Usage

### Basic: Generate Local Markdown Plan

Generate a plan from sample segments and save to local markdown file:

```bash
python examples/google_docs_example.py
```

This will:
1. Load `examples/sample_segments.json`
2. Extract plan sections using keyword classification
3. Generate markdown formatted plan
4. Save to `output/example_plan.md`

### Advanced: Publish to Google Docs

Publish the generated plan to Google Docs:

```bash
python examples/google_docs_example.py --publish
```

Prerequisites:
- Google Cloud project with Docs API enabled
- OAuth credentials downloaded to `config/credentials.json`
- Configuration file at `config/google_docs.ini`

See [docs/google_docs_setup.md](../docs/google_docs_setup.md) for setup instructions.

### Share with Collaborators

Publish and share with specific users:

```bash
python examples/google_docs_example.py \
    --publish \
    --share alice@example.com \
    --share bob@example.com \
    --role writer
```

Options:
- `--share EMAIL` - Share with email address (can be used multiple times)
- `--role ROLE` - Sharing permission: `reader`, `writer`, or `commenter` (default: writer)

### Custom Input

Use your own transcript segments:

```bash
python examples/google_docs_example.py \
    --segments path/to/your/segments.json \
    --output path/to/output.md \
    --title "My Custom Plan"
```

## Command-Line Tool

For production use, use the main pipeline script with LLM-based plan extraction:

```bash
# Generate local markdown using Claude (default)
python -m pipeline.plan_from_transcript \
    --input segments.json \
    --output plan.md

# Use GPT instead of Claude
python -m pipeline.plan_from_transcript \
    --input segments.json \
    --output plan.md \
    --model gpt

# Generate and publish to Google Docs
python -m pipeline.plan_from_transcript \
    --input segments.json \
    --google-docs \
    --google-docs-title "Project Plan"
```

**Note:** Requires API key for Claude (ANTHROPIC_API_KEY) or GPT (OPENAI_API_KEY).

## Sample Segments Format

Transcript segments should be JSON with this structure:

```json
{
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 8.5,
      "text": "Welcome everyone...",
      "timestamp": "00:00",
      "speaker": "Alice"
    }
  ],
  "metadata": {
    "source": "meeting.wav",
    "duration": 159.2,
    "language": "en"
  }
}
```

Required fields per segment:
- `text` - The transcribed text
- `timestamp` - Display timestamp (e.g., "00:00" or "00:00:00")
- `speaker` - Speaker name or ID (optional, defaults to "Unknown")

## Plan Section Extraction

The plan generator uses LLM (Claude or GPT) to intelligently extract structured sections from transcripts:

- **Problem Statement** - What problem is being solved? What pain points are mentioned?
- **Target Users** - Who will use this? What are their characteristics?
- **Goals & Objectives** - What are the desired outcomes? What success metrics are mentioned?
- **Acceptance Criteria** - What conditions must be met? What defines "done"?
- **Risks & Assumptions** - What challenges, dependencies, or assumptions are mentioned?
- **Additional Notes** - Any other important context, decisions, or action items

The LLM analyzes the entire transcript contextually rather than using simple keyword matching.

## Troubleshooting

### Import Errors

If you get import errors when running examples:

```bash
# Ensure you're in the project root
cd /path/to/TalkSmith-issue-16

# Install dependencies
pip install -r requirements.txt

# Run from project root
python examples/google_docs_example.py
```

### Google Docs Authentication

First time publishing to Google Docs will open a browser for authentication:

1. Sign in to your Google account
2. Grant permission to access Google Docs and Drive
3. Token saved to `config/token.json` for future use

If authentication fails:
- Delete `config/token.json` and try again
- Verify credentials file exists at `config/credentials.json`
- Check API is enabled in Google Cloud Console

See [docs/google_docs_setup.md](../docs/google_docs_setup.md) for detailed setup instructions.

## Next Steps

- Review [docs/google_docs_setup.md](../docs/google_docs_setup.md) for Google Docs integration
- Check [pipeline/plan_from_transcript.py](../pipeline/plan_from_transcript.py) for implementation details
- Run tests: `pytest tests/test_plan_from_transcript.py`
