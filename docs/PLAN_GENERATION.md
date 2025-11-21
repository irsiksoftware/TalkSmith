# Plan Generation from Transcripts

Generate structured PRD (Product Requirements Document) and project plans from meeting transcripts using AI-powered extraction.

## Overview

The plan generation feature transforms raw meeting or interview transcripts into actionable, structured documents. It uses LLM technology (Claude or GPT) to intelligently extract:

- **Problem Statement**: What problem is being solved?
- **Target Users**: Who will use this solution?
- **Goals & Objectives**: What are the desired outcomes?
- **Acceptance Criteria**: What defines "done"?
- **Risks & Assumptions**: What challenges or dependencies exist?
- **Additional Notes**: Important context, decisions, or action items

## Quick Start

### Prerequisites

1. Install LLM provider dependencies:

```bash
# For Claude (recommended)
pip install anthropic

# OR for GPT
pip install openai
```

2. Set up API keys:

```bash
# For Claude
export ANTHROPIC_API_KEY="your-api-key-here"

# OR for GPT
export OPENAI_API_KEY="your-api-key-here"
```

### Basic Usage

Generate a plan from transcript segments:

```bash
python -m cli.main plan data/outputs/meeting_segments.json
```

This will:

1. Load the transcript segments
2. Convert to readable format with timestamps and speakers
3. Send to LLM for structured extraction
4. Generate a markdown plan document
5. Save to `meeting_segments_plan.md`

## Command-Line Options

```bash
python -m cli.main plan [OPTIONS] INPUT_FILE
```

### Options

- `INPUT_FILE` (required): Path to segments JSON file
- `-o, --output`: Custom output path for markdown file (default: `<input>_plan.md`)
- `-t, --title`: Custom plan title (default: derived from filename)
- `--model`: LLM model to use - `claude` or `gpt` (default: `claude`)
- `--google-docs`: Upload plan to Google Docs after generation
- `--google-docs-title`: Custom title for Google Docs document

### Examples

#### Basic plan generation

```bash
python -m cli.main plan data/outputs/interview.json
```

#### Custom output path and title

```bash
python -m cli.main plan data/outputs/meeting.json \
  -o plans/auth_project.md \
  -t "Authentication Enhancement Project"
```

#### Using GPT instead of Claude

```bash
python -m cli.main plan data/outputs/brainstorm.json --model gpt
```

#### Generate and upload to Google Docs

```bash
python -m cli.main plan data/outputs/strategy.json \
  --google-docs \
  --google-docs-title "Q1 Strategy Discussion"
```

## Google Docs Integration

### Setup

1. **Create Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the following APIs:
     - Google Docs API
     - Google Drive API

2. **Create OAuth Credentials**:
   - Navigate to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app" as application type
   - Download the credentials file

3. **Configure TalkSmith**:

   ```bash
   # Copy example configuration
   cp config/google_docs.ini.example config/google_docs.ini

   # Place your credentials file
   mv ~/Downloads/credentials.json config/credentials.json
   ```

4. **Edit Configuration** (`config/google_docs.ini`):

   ```ini
   [google_docs]
   credentials_file = config/credentials.json
   token_file = config/token.json

   # Sharing settings
   sharing = private  # Options: private, anyone, domain
   domain =           # Your domain if sharing=domain
   ```

5. **First-time Authentication**:
   - On first use, a browser window will open
   - Sign in with your Google account
   - Grant the requested permissions
   - Token is saved to `config/token.json` for future use

### Sharing Options

Configure document sharing in `config/google_docs.ini`:

- **Private** (default): Only you can access

  ```ini
  sharing = private
  ```

- **Anyone with link**: Anyone with the URL can view

  ```ini
  sharing = anyone
  ```

- **Domain-wide**: Anyone in your organization can view

  ```ini
  sharing = domain
  domain = yourcompany.com
  ```

## Python API

You can also use the plan generation feature programmatically:

```python
from pathlib import Path
from pipeline.plan_from_transcript import PlanGenerator

# Initialize generator
generator = PlanGenerator(model_type='claude')

# Generate plan
plan_md = generator.generate_plan(
    segments_path=Path('data/outputs/meeting.json'),
    output_path=Path('plans/meeting_plan.md'),
    title='Sprint Planning Session'
)

print(f"Plan generated: {len(plan_md)} characters")
```

### With Google Docs Upload

```python
from pipeline.plan_from_transcript import PlanGenerator
from pipeline.google_docs_integration import GoogleDocsUploader

# Generate plan
generator = PlanGenerator(model_type='claude')
plan_md = generator.generate_plan(
    segments_path=Path('data/outputs/meeting.json'),
    title='Sprint Planning'
)

# Upload to Google Docs
uploader = GoogleDocsUploader()
doc_url = uploader.create_document_from_markdown(
    plan_md,
    title='Sprint Planning Session'
)

print(f"Google Docs URL: {doc_url}")
```

## Output Format

Generated plans use the following markdown structure:

```markdown
# [Plan Title]

**Date:** 2025-10-17
**Source:** meeting_segments.json

## Problem Statement
[Extracted problem description]

## Target Users
[Identified user groups and characteristics]

## Goals & Objectives
[Desired outcomes and success metrics]

## Acceptance Criteria
[Conditions that must be met]

## Risks & Assumptions
[Challenges, dependencies, and assumptions]

## Additional Notes
[Context, decisions, action items]
```

## Input Format

The plan generator expects transcript segments in JSON format:

### Array Format

```json
[
  {
    "text": "We need to improve the login flow",
    "start": 15.5,
    "speaker": "Alice"
  },
  {
    "text": "The main users are developers",
    "start": 23.8,
    "speaker": "Bob"
  }
]
```

### Object Format

```json
{
  "segments": [
    {
      "text": "We need to improve the login flow",
      "start": 15.5,
      "speaker": "Alice"
    }
  ],
  "metadata": {
    "duration": 300
  }
}
```

## Workflow Examples

### Complete Meeting to Plan Workflow

1. **Record and transcribe meeting**:

   ```bash
   python -m cli.main transcribe data/inputs/meeting.mp3 \
     --diarize \
     --num-speakers 3
   ```

2. **Generate plan from transcript**:

   ```bash
   python -m cli.main plan data/outputs/meeting_diarized.json \
     -t "Authentication Enhancement Plan"
   ```

3. **Upload to Google Docs for team collaboration**:

   ```bash
   python -m cli.main plan data/outputs/meeting_diarized.json \
     --google-docs \
     --google-docs-title "Auth Enhancement - Team Review"
   ```

### Batch Processing Multiple Meetings

```python
from pathlib import Path
from pipeline.plan_from_transcript import PlanGenerator
from pipeline.google_docs_integration import GoogleDocsUploader

# Initialize
generator = PlanGenerator(model_type='claude')
uploader = GoogleDocsUploader()

# Process all meetings
for segments_file in Path('data/outputs').glob('*_segments.json'):
    print(f"Processing: {segments_file.name}")

    # Generate plan
    plan_md = generator.generate_plan(
        segments_path=segments_file,
        output_path=segments_file.parent / f"{segments_file.stem}_plan.md"
    )

    # Upload to Google Docs
    doc_url = uploader.create_document_from_markdown(
        plan_md,
        title=f"Plan: {segments_file.stem}"
    )

    print(f"  ✓ Google Doc: {doc_url}")
```

## Troubleshooting

### LLM API Issues

**Problem**: `ImportError: anthropic package not installed`

**Solution**: Install the required package:

```bash
pip install anthropic
# or
pip install openai
```

**Problem**: `Authentication error: Invalid API key`

**Solution**: Check your environment variable:

```bash
# For Claude
echo $ANTHROPIC_API_KEY

# For GPT
echo $OPENAI_API_KEY
```

### Google Docs Issues

**Problem**: `FileNotFoundError: credentials.json not found`

**Solution**: Download credentials from Google Cloud Console and place in `config/` directory.

**Problem**: `Failed to create Google Doc: insufficient permissions`

**Solution**:

1. Ensure Google Docs API and Google Drive API are enabled
2. Re-authenticate by deleting `config/token.json` and running the command again
3. Grant all requested permissions during OAuth flow

**Problem**: `HttpError 403: Access Not Configured`

**Solution**: Enable the required APIs in your Google Cloud project:

- Google Docs API
- Google Drive API

### Plan Quality Issues

**Problem**: Plan sections say "Not specified in transcript"

**Solution**:

- Ensure transcript has sufficient detail and context
- Meeting discussions should explicitly cover problems, users, goals, etc.
- Consider using more detailed transcripts (with diarization)

**Problem**: Plan extraction is inaccurate

**Solution**:

- Try using a different model (`--model gpt` instead of `claude`)
- Ensure transcript segments have proper speaker attribution
- Review and edit the generated markdown as needed

## Best Practices

1. **Use Speaker Diarization**: Plans are more accurate when transcript includes speaker labels

   ```bash
   python -m cli.main transcribe audio.mp3 --diarize
   ```

2. **Review Generated Plans**: LLM extraction is powerful but not perfect - always review output

3. **Iterative Refinement**: If plan quality is poor, try:
   - Different LLM model (`claude` vs `gpt`)
   - Better quality transcripts (preprocessing, denoising)
   - More structured meeting discussions

4. **Version Control**: Keep generated plans in version control for tracking changes

5. **Google Docs for Collaboration**: Use local markdown for individual work, Google Docs for team collaboration

## Cost Considerations

### LLM API Costs

- **Claude**: ~$3 per million input tokens, ~$15 per million output tokens
- **GPT-4**: ~$30 per million input tokens, ~$60 per million output tokens

Typical costs per transcript:

- 30-minute meeting (~10,000 tokens): $0.03-0.30
- 1-hour interview (~20,000 tokens): $0.06-0.60

### Google Docs API

- **Free**: Up to quota limits (sufficient for most users)
- No charge for document creation or storage

## Configuration Reference

### Environment Variables

```bash
# LLM API Keys
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
```

### Configuration File (`config/google_docs.ini`)

```ini
[google_docs]
# OAuth credentials from Google Cloud Console
credentials_file = config/credentials.json

# Auto-generated token (don't commit to version control)
token_file = config/token.json

# Sharing: private, anyone, domain
sharing = private

# Domain for domain-wide sharing
domain = example.com

# Optional: Google Drive folder ID
folder_id =
```

## Related Documentation

- [CLI Guide](CLI.md) - Complete CLI reference
- [Transcription Guide](TRANSCRIPTION.md) - Audio transcription workflow
- [Export Formats](EXPORT_FORMATS.md) - Output format options

## Support

For issues, questions, or feature requests:

- GitHub Issues: <https://github.com/irsiksoftware/TalkSmith/issues>
- Issue #16: <https://github.com/irsiksoftware/TalkSmith/issues/16>
