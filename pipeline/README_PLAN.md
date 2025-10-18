# Plan Generation Module

This directory contains the plan generation and Google Docs integration modules for TalkSmith.

## Files

### `plan_from_transcript.py`
Core module for generating structured PRD/plan documents from transcript segments using LLM technology.

**Key Classes:**
- `PlanGenerator`: Main class for plan generation
  - Supports both Claude and GPT models
  - Converts transcript segments to readable format
  - Extracts structured plan data using LLM prompts
  - Generates markdown-formatted plans

**Usage:**
```python
from pipeline.plan_from_transcript import PlanGenerator

generator = PlanGenerator(model_type='claude')
plan_md = generator.generate_plan(
    segments_path='meeting.json',
    output_path='meeting_plan.md',
    title='Sprint Planning'
)
```

**CLI Usage:**
```bash
python -m pipeline.plan_from_transcript \
  --input segments.json \
  --output plan.md \
  --model claude
```

### `google_docs_integration.py`
Module for uploading plan documents to Google Docs via OAuth 2.0 authentication.

**Key Classes:**
- `GoogleDocsUploader`: Client for Google Docs API
  - OAuth 2.0 authentication flow
  - Document creation from markdown
  - Document updating
  - Sharing and permissions management

**Usage:**
```python
from pipeline.google_docs_integration import GoogleDocsUploader

uploader = GoogleDocsUploader()
doc_url = uploader.create_document_from_markdown(
    markdown_content=plan_md,
    title='Project Plan'
)
print(f"Document URL: {doc_url}")
```

## Dependencies

### Required for Plan Generation
```bash
# Install at least one LLM provider
pip install anthropic  # For Claude models
pip install openai     # For GPT models
```

### Required for Google Docs Integration
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## Configuration

### LLM API Keys
Set environment variables for your chosen LLM provider:

```bash
# For Claude
export ANTHROPIC_API_KEY="your-api-key"

# For GPT
export OPENAI_API_KEY="your-api-key"
```

### Google Docs Setup

1. Copy example configuration:
   ```bash
   cp config/google_docs.ini.example config/google_docs.ini
   ```

2. Download OAuth credentials from Google Cloud Console:
   - Enable Google Docs API and Google Drive API
   - Create OAuth 2.0 credentials (Desktop app)
   - Save as `config/credentials.json`

3. Edit `config/google_docs.ini`:
   ```ini
   [google_docs]
   credentials_file = config/credentials.json
   token_file = config/token.json
   sharing = private
   ```

## Plan Template

Generated plans follow this structure:

```markdown
# [Title]

**Date:** YYYY-MM-DD
**Source:** filename.json

## Problem Statement
[What problem is being solved?]

## Target Users
[Who will use this?]

## Goals & Objectives
[What are the desired outcomes?]

## Acceptance Criteria
[What defines "done"?]

## Risks & Assumptions
[What challenges exist?]

## Additional Notes
[Context, decisions, action items]
```

## LLM Extraction Prompt

The module uses a structured prompt to extract plan information from transcripts:

1. **Problem Statement**: Pain points and issues mentioned
2. **Target Users**: User characteristics and demographics
3. **Goals & Objectives**: Desired outcomes and success metrics
4. **Acceptance Criteria**: Conditions that must be met
5. **Risks & Assumptions**: Challenges and dependencies
6. **Additional Notes**: Other important context

The LLM responds in JSON format, which is then formatted into the markdown template.

## Error Handling

### Plan Generation Errors
- **ImportError**: LLM package not installed
  - Solution: `pip install anthropic` or `pip install openai`
- **ValueError**: Invalid model type or segment format
  - Check model parameter and JSON structure
- **API Errors**: Authentication or rate limit issues
  - Verify API keys and check provider status

### Google Docs Errors
- **FileNotFoundError**: Missing credentials file
  - Download from Google Cloud Console
- **HttpError 403**: API not enabled or permissions issue
  - Enable Google Docs/Drive APIs
  - Re-authenticate and grant permissions
- **HttpError 404**: Document not found (for updates)
  - Verify document ID

## Testing

Run the test suite:
```bash
pytest tests/test_plan_from_transcript.py -v
```

Test coverage includes:
- PlanGenerator initialization (Claude and GPT)
- Segment loading (array and object formats)
- Text conversion with timestamps
- LLM extraction (mocked API calls)
- Plan generation workflow
- Template formatting

## Examples

### Basic Plan Generation
```python
from pathlib import Path
from pipeline.plan_from_transcript import PlanGenerator

generator = PlanGenerator(model_type='claude')
plan = generator.generate_plan(
    segments_path=Path('meeting.json'),
    output_path=Path('plan.md')
)
```

### With Google Docs Upload
```python
from pipeline.plan_from_transcript import PlanGenerator
from pipeline.google_docs_integration import GoogleDocsUploader

# Generate plan
generator = PlanGenerator(model_type='gpt')
plan_md = generator.generate_plan(
    segments_path=Path('meeting.json'),
    title='Sprint Planning'
)

# Upload to Google Docs
uploader = GoogleDocsUploader()
doc_url = uploader.create_document_from_markdown(plan_md, 'Sprint Plan')
```

### Batch Processing
```python
from pathlib import Path
from pipeline.plan_from_transcript import PlanGenerator

generator = PlanGenerator(model_type='claude')

for segments_file in Path('transcripts').glob('*.json'):
    output_file = segments_file.parent / f"{segments_file.stem}_plan.md"
    generator.generate_plan(segments_file, output_file)
    print(f"Generated: {output_file}")
```

## Integration with TalkSmith Pipeline

The plan generation module integrates seamlessly with the transcription pipeline:

```bash
# 1. Transcribe with diarization
python -m cli.main transcribe meeting.mp3 --diarize

# 2. Generate plan from segments
python -m cli.main plan data/outputs/meeting_diarized.json \
  --google-docs \
  --google-docs-title "Team Meeting Plan"
```

## Performance Considerations

### Token Usage
- Average meeting (30 min): ~10,000 input tokens
- LLM response: ~1,000 output tokens
- Typical API call: 1-3 seconds

### Cost Estimates
- Claude: $0.03-0.05 per plan
- GPT-4: $0.30-0.60 per plan

### Optimization Tips
1. Use Claude for cost efficiency
2. Batch process multiple plans
3. Cache common prompts
4. Consider using smaller models for simple extractions

## Security Notes

### API Keys
- Never commit API keys to version control
- Use environment variables or secure vaults
- Rotate keys periodically

### Google OAuth
- Keep `credentials.json` secure (add to .gitignore)
- Token file is auto-generated and contains access tokens
- Use domain-restricted credentials when possible

### Data Privacy
- Transcripts may contain sensitive information
- Consider on-premises LLM for confidential data
- Review sharing settings before uploading to Google Docs

## Contributing

When extending this module:
1. Maintain backward compatibility with existing segments format
2. Add tests for new features
3. Update documentation
4. Follow existing code style
5. Consider token usage and API costs

## Related Modules

- `outline_from_segments.py`: Generates timestamped outlines (no LLM)
- `exporters.py`: Export segments to various formats
- `transcribe_fw.py`: Audio transcription
- `diarize_alt.py`: Speaker diarization

## References

- [TalkSmith Plan Generation Docs](../docs/PLAN_GENERATION.md)
- [Google Docs API Documentation](https://developers.google.com/docs/api)
- [Anthropic Claude API](https://docs.anthropic.com/claude/reference)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
