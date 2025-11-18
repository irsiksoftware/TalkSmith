# Google Docs Integration Setup Guide

This guide explains how to set up the Google Docs API integration for TalkSmith to automatically publish plan documents to Google Docs.

## Overview

The Google Docs integration allows you to:

- Convert transcript segments into structured PRD/plan documents using LLM
- Automatically push plans to Google Docs for collaborative editing
- Share documents with team members
- Manage multiple plan documents from transcripts

## Prerequisites

- Python 3.8 or higher
- A Google account
- Access to Google Cloud Console
- API key for either Anthropic (Claude) or OpenAI (GPT)

## Setup Steps

### 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" at the top, then "New Project"
3. Enter a project name (e.g., "TalkSmith Google Docs")
4. Click "Create"

### 2. Enable Required APIs

1. In your Google Cloud project, navigate to "APIs & Services" > "Library"
2. Search for and enable the following APIs:
   - **Google Docs API**
   - **Google Drive API**

### 3. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" user type
   - Fill in required fields (app name, user support email, developer email)
   - Add your email to "Test users" (for development)
   - Save and continue
4. Back on the credentials page, select "Desktop app" as the application type
5. Enter a name (e.g., "TalkSmith Desktop Client")
6. Click "Create"
7. Download the credentials JSON file

### 4. Install Required Dependencies

Install LLM provider (choose one or both):

```bash
# For Claude (recommended)
pip install anthropic

# For GPT
pip install openai
```

Install Google Docs integration:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

Or install all dependencies from requirements.txt:

```bash
pip install -r requirements.txt
```

### 5. Configure LLM API Key

Set your API key as an environment variable:

```bash
# For Claude
export ANTHROPIC_API_KEY="sk-ant-..."

# For GPT
export OPENAI_API_KEY="sk-..."
```

Or add to your `.env` file (recommended for development).

### 6. Configure Google Docs

1. Copy the example configuration file:

   ```bash
   cp config/google_docs.ini.example config/google_docs.ini
   ```

2. Move the downloaded credentials file to your project:

   ```bash
   mv ~/Downloads/client_secret_*.json config/credentials.json
   ```

3. Edit `config/google_docs.ini` to set the credentials path:

   ```ini
   [google_docs]
   credentials_file = config/credentials.json
   token_file = config/token.json
   sharing = private
   ```

### 7. First-Time Authentication

The first time you run the Google Docs integration, you'll need to authenticate:

```bash
python -m pipeline.plan_from_transcript --input segments.json --google-docs --google-docs-title "My Plan"
```

This will:

1. Open your web browser
2. Ask you to sign in to your Google account
3. Request permission to access Google Docs and Drive
4. Save an authentication token to `config/token.json` for future use

**Important:** The token file contains sensitive credentials. Never commit it to version control.

## Usage

### Basic Usage: Generate Local Markdown

```bash
# Using Claude (default)
python -m pipeline.plan_from_transcript --input segments.json --output plan.md

# Using GPT
python -m pipeline.plan_from_transcript --input segments.json --output plan.md --model gpt
```

### Push to Google Docs

```bash
# Generate plan and upload to Google Docs
python -m pipeline.plan_from_transcript \
    --input segments.json \
    --google-docs \
    --google-docs-title "Project Plan"

# Specify custom title and model
python -m pipeline.plan_from_transcript \
    --input segments.json \
    --output plan.md \
    --google-docs \
    --title "Product Requirements" \
    --google-docs-title "Q4 2025 Product Requirements" \
    --model claude
```

## Configuration Options

Edit `config/google_docs.ini` to customize behavior:

```ini
[google_docs]
# Path to OAuth credentials (required)
credentials_file = config/credentials.json

# Path to store auth token (auto-generated)
token_file = config/token.json

# Sharing settings: private, anyone, domain
sharing = private

# Domain for domain-wide sharing (optional)
domain = example.com

# Google Drive folder ID (optional)
folder_id = 1a2b3c4d5e6f7g8h9i
```

### Sharing Options

- **private** (default): Only you can access the document
- **anyone**: Anyone with the link can view the document
- **domain**: Anyone in your organization domain can view the document

## Troubleshooting

### "credentials.json not found"

Make sure you've downloaded the OAuth credentials from Google Cloud Console and placed them in the correct location specified in `config/google_docs.ini`.

### "Invalid client_id"

The credentials file may be corrupted or for a different application type. Download fresh credentials from Google Cloud Console and ensure you selected "Desktop app" as the application type.

### "Access denied" or "Insufficient permissions"

1. Check that you've enabled both Google Docs API and Google Drive API
2. Delete `config/token.json` and re-authenticate
3. Ensure your Google account has permission to create documents

### "Token expired"

Delete `config/token.json` and run the script again to re-authenticate.

### Browser doesn't open during authentication

The OAuth flow requires a browser. If you're on a headless server:

1. Run the script on your local machine first to generate `token.json`
2. Copy `token.json` to your server
3. Update `config/google_docs.ini` to point to this token file

## Security Best Practices

1. **Never commit credentials to version control:**
   - Add `config/credentials.json` to `.gitignore`
   - Add `config/token.json` to `.gitignore`
   - Add `config/google_docs.ini` to `.gitignore`

2. **Use service accounts for production:**
   - For automated systems, consider using service account credentials instead of OAuth

3. **Limit API scopes:**
   - The integration only requests necessary scopes (documents and drive.file)
   - Never grant more permissions than needed

4. **Rotate credentials regularly:**
   - Periodically regenerate OAuth credentials in Google Cloud Console
   - Update your configuration files accordingly

## Example Workflow

Here's a complete workflow from transcript to Google Doc:

```bash
# 1. Transcribe audio
python pipeline/transcribe.py meeting.mp3 --output segments.json

# 2. Generate plan and push to Google Docs
python pipeline/plan_from_transcript.py segments.json \
    --google-docs \
    --title "Q4 Product Planning Meeting"

# Output: Success! Document created: https://docs.google.com/document/d/...
```

## Support

For issues specific to Google Docs API:

- [Google Docs API Documentation](https://developers.google.com/docs/api)
- [Google Drive API Documentation](https://developers.google.com/drive/api)

For TalkSmith-specific issues:

- Check existing [GitHub Issues](https://github.com/irsiksoftware/TalkSmith/issues)
- Create a new issue with the `google-docs` label
