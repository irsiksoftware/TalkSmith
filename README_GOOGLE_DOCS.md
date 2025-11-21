# Google Docs Integration for TalkSmith

Generate structured plan documents from transcripts and publish to Google Docs.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate Plan Locally

```bash
python pipeline/plan_from_transcript.py examples/sample_segments.json -o my_plan.md
```

### 3. Publish to Google Docs (Optional)

First-time setup required. See [docs/google_docs_setup.md](docs/google_docs_setup.md) for detailed instructions.

```bash
python pipeline/plan_from_transcript.py examples/sample_segments.json --google-doc "My Project Plan"
```

## Features

### Plan Generation

Automatically extracts and organizes transcript content into structured sections:

- **Problem Statement** - Issues and challenges identified
- **Target Users** - User personas and stakeholder groups
- **Goals & Objectives** - Project aims and success metrics
- **Acceptance Criteria** - Requirements and must-haves
- **Risks & Considerations** - Concerns and blockers
- **Additional Notes** - Other relevant information

### Smart Classification

Uses keyword matching to automatically categorize transcript segments into appropriate plan sections.

### Action Item Extraction

Identifies and extracts actionable items based on verbs like:

- implement, create, build, develop, add
- design, test, deploy, integrate, ensure

## Usage Examples

### Basic Plan Generation

```bash
# Generate markdown plan
python pipeline/plan_from_transcript.py segments.json -o plan.md

# Custom title
python pipeline/plan_from_transcript.py segments.json -t "Q1 Sprint Plan" -o sprint_plan.md

# Preview without saving
python pipeline/plan_from_transcript.py segments.json --dry-run
```

### Google Docs Publishing

```bash
# Create new document
python pipeline/plan_from_transcript.py segments.json --google-doc "Product Roadmap"

# Both local and Google Docs
python pipeline/plan_from_transcript.py segments.json \
  -o local_backup.md \
  --google-doc "Product Roadmap"
```

### Pipeline Integration

```bash
# Full workflow
python pipeline/transcribe_audio.py meeting.wav
python pipeline/outline_from_segments.py segments.json
python pipeline/plan_from_transcript.py segments.json --google-doc "Meeting Notes - $(date +%Y-%m-%d)"
```

## File Structure

```
pipeline/
├── plan_from_transcript.py      # Main script
├── google_docs_integration.py   # Google Docs API wrapper
└── outline_from_segments.py     # Existing outline generator

config/
└── google_docs.ini.example      # Configuration template

docs/
└── google_docs_setup.md         # Detailed setup guide

examples/
└── sample_segments.json         # Example transcript

tests/
└── test_plan_from_transcript.py # Unit tests
```

## Configuration

Copy and customize configuration:

```bash
cp config/google_docs.ini.example config/google_docs.ini
```

Edit `config/google_docs.ini`:

```ini
[credentials]
credentials_file = credentials.json
token_file = ~/.talksmith/google_token.pickle

[defaults]
title_template = TalkSmith Plan - {date}
```

## Testing

Run unit tests:

```bash
pytest tests/test_plan_from_transcript.py -v
```

Test with sample data:

```bash
python pipeline/plan_from_transcript.py examples/sample_segments.json --dry-run
```

## Google Docs Setup

### Prerequisites

1. Google account
2. Google Cloud project with Docs API enabled
3. OAuth 2.0 credentials (credentials.json)

### Setup Steps

See [docs/google_docs_setup.md](docs/google_docs_setup.md) for complete instructions:

1. Enable Google Docs API
2. Create OAuth credentials
3. Download credentials.json
4. First-time authorization

### Quick Setup

```bash
# 1. Download credentials from Google Cloud Console
# 2. Save as credentials.json in project root
# 3. Run first command (opens browser for auth)
python pipeline/plan_from_transcript.py segments.json --google-doc "Test"
```

## Customization

### Modify Section Keywords

Edit `plan_from_transcript.py`:

```python
SECTION_KEYWORDS = {
    'problem': ['problem', 'issue', 'challenge'],
    'users': ['user', 'customer', 'stakeholder'],
    # Add your own keywords
}
```

### Custom Markdown Template

Override `format_markdown()` method:

```python
class CustomPlanGenerator(PlanGenerator):
    def format_markdown(self, plan, title):
        # Your custom formatting
        return custom_markdown
```

## Troubleshooting

### Common Issues

**"credentials.json not found"**

- Download from Google Cloud Console
- Place in project root or set `GOOGLE_CREDENTIALS_PATH`

**"No plan content extracted"**

- Check segments.json format
- Verify segments have 'text' field
- Review keyword matching in code

**"Google API error"**

- Enable Google Docs API in Cloud Console
- Check credentials.json is valid
- Verify token hasn't expired

### Debug Mode

```bash
# Preview classification results
python pipeline/plan_from_transcript.py segments.json --dry-run | less
```

## Security

**Important:** Never commit these files:

- `credentials.json` - OAuth client secret
- `google_token.pickle` - User authorization
- `config/google_docs.ini` - May contain sensitive paths

These are already in `.gitignore`.

## API Limits

Google Docs API quotas:

- **Read:** 300 requests/minute
- **Write:** 60 requests/minute

For high-volume usage, implement rate limiting or request quota increase.

## Roadmap

- [ ] Template-based plan generation
- [ ] Custom section definitions via config
- [ ] Batch processing for multiple transcripts
- [ ] Google Drive folder organization
- [ ] Team sharing automation
- [ ] Export to other formats (PDF, DOCX)

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## Support

- **Documentation:** [docs/google_docs_setup.md](docs/google_docs_setup.md)
- **Issues:** [GitHub Issues](https://github.com/irsiksoftware/TalkSmith/issues)
- **Examples:** [examples/](examples/)

## License

See main repository LICENSE file.

## Related Documentation

- [Google Docs API](https://developers.google.com/docs/api)
- [TalkSmith Main README](README.md)
- [Pipeline Documentation](docs/pipeline.md)
