# Google Docs Integration Setup Guide

This guide explains how to set up Google Docs API integration for TalkSmith to publish generated plans directly to Google Docs.

## Overview

The Google Docs integration allows you to:
- Automatically create Google Docs from generated plans
- Share documents with team members
- Organize documents in specific Google Drive folders
- Enable collaborative editing of PRD/plan documents

## Prerequisites

- Google Cloud Platform (GCP) account
- Python 3.8 or higher
- TalkSmith installed with required dependencies

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name (e.g., "TalkSmith Integration")
4. Click "Create"
5. Wait for project creation to complete

## Step 2: Enable Required APIs

1. In the Google Cloud Console, navigate to "APIs & Services" → "Library"
2. Search for and enable the following APIs:
   - **Google Docs API**
   - **Google Drive API**

For each API:
- Click on the API name
- Click "Enable"
- Wait for activation

## Step 3: Create Service Account

1. Navigate to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Enter service account details:
   - **Name:** TalkSmith Document Publisher
   - **Description:** Service account for automated document creation
4. Click "Create and Continue"
5. Skip optional role assignment (click "Continue")
6. Click "Done"

## Step 4: Generate Service Account Key

1. In the Credentials page, find your service account under "Service Accounts"
2. Click on the service account email
3. Go to the "Keys" tab
4. Click "Add Key" → "Create new key"
5. Select "JSON" format
6. Click "Create"
7. Save the downloaded JSON file securely

**Important:** This file contains sensitive credentials. Never commit it to version control.

## Step 5: Configure TalkSmith

1. Move the credentials file to your TalkSmith config directory:
   ```bash
   mkdir -p config
   mv ~/Downloads/your-service-account-key.json config/service-account-credentials.json
   ```

2. Copy the example configuration:
   ```bash
   cp config/google_docs.ini.example config/google_docs.ini
   ```

3. Edit `config/google_docs.ini`:
   ```ini
   [google_docs]
   credentials_file = config/service-account-credentials.json
   folder_id = <optional-folder-id>
   share_with_emails = user1@example.com, user2@example.com
   share_permission = writer
   ```

## Step 6: Optional - Set Up Shared Folder

To organize all generated documents in a specific folder:

1. Create a folder in Google Drive
2. Open the folder in your browser
3. Copy the folder ID from the URL:
   ```
   https://drive.google.com/drive/folders/FOLDER_ID_HERE
   ```
4. Add the folder ID to `config/google_docs.ini`
5. Share the folder with the service account email:
   - Right-click folder → "Share"
   - Add service account email (found in credentials JSON: `client_email`)
   - Set permission to "Editor"

## Step 7: Install Python Dependencies

Install required Google API libraries:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

Or install all TalkSmith dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Generate and Publish Plan to Google Docs

```bash
# Generate plan from transcript segments
python pipeline/plan_from_transcript.py \
  data/segments.json \
  --output output/plan.md \
  --google-docs

# Or publish existing plan separately
python pipeline/google_docs_integration.py data/segments.json
```

### Command Line Options

```bash
python pipeline/plan_from_transcript.py --help

Options:
  segments_file          Path to transcript segments JSON
  -o, --output          Output file path (default: plan.md)
  -f, --format          Output format: markdown or json (default: markdown)
  -t, --title           Custom plan title
  --google-docs         Publish to Google Docs after generation
```

## Configuration Options

### credentials_file
Path to service account JSON key file.

**Required:** Yes

**Example:** `config/service-account-credentials.json`

### folder_id
Google Drive folder ID where documents will be created.

**Required:** No (creates in root if not specified)

**Example:** `1a2b3c4d5e6f7g8h9i0j`

### share_with_emails
Comma-separated list of email addresses to automatically share documents with.

**Required:** No

**Example:** `alice@example.com, bob@example.com`

### share_permission
Permission level for shared users.

**Required:** No (defaults to `writer`)

**Options:**
- `reader` - View only
- `commenter` - Can add comments
- `writer` - Can edit

## Troubleshooting

### Error: "Credentials file not found"

**Solution:** Verify the `credentials_file` path in `config/google_docs.ini` is correct and the file exists.

### Error: "API has not been enabled"

**Solution:** Ensure Google Docs API and Google Drive API are enabled in your GCP project.

### Error: "Permission denied"

**Solution:**
1. Check that the service account has access to the folder (if `folder_id` is specified)
2. Share the folder with the service account email address

### Error: "Invalid credentials"

**Solution:**
1. Verify the JSON credentials file is not corrupted
2. Regenerate service account key if necessary
3. Ensure credentials file has correct permissions

### Documents not appearing in shared folder

**Solution:**
1. Verify `folder_id` is correct
2. Share folder with service account email (found in credentials JSON)
3. Grant "Editor" permission to service account

### Auto-sharing not working

**Solution:**
1. Check `share_with_emails` is properly formatted (comma-separated, no quotes)
2. Verify email addresses are correct
3. Check Google Drive API is enabled

## Security Best Practices

1. **Never commit credentials to version control**
   - Add to `.gitignore`:
     ```
     config/google_docs.ini
     config/*.json
     ```

2. **Restrict service account permissions**
   - Only grant necessary API access
   - Use folder-level sharing instead of organization-wide access

3. **Rotate credentials periodically**
   - Generate new service account keys every 90 days
   - Delete old keys after rotation

4. **Monitor API usage**
   - Check Google Cloud Console for unusual activity
   - Set up billing alerts

## API Limits

Google Docs API has the following limits:
- **Read requests:** 300 per minute per user
- **Write requests:** 60 per minute per user

For high-volume use cases:
- Implement exponential backoff
- Batch multiple operations
- Cache results where possible

## Example Workflow

Complete workflow from transcript to Google Doc:

```bash
# 1. Transcribe audio
python pipeline/transcribe.py audio/meeting.mp3 --output data/segments.json

# 2. Generate and publish plan
python pipeline/plan_from_transcript.py \
  data/segments.json \
  --title "Q4 Product Planning Meeting" \
  --google-docs

# Output:
# Plan generated successfully
# Document created: https://docs.google.com/document/d/DOCUMENT_ID/edit
# Shared with: alice@example.com, bob@example.com
```

## Additional Resources

- [Google Docs API Documentation](https://developers.google.com/docs/api)
- [Google Drive API Documentation](https://developers.google.com/drive/api)
- [Service Account Authentication](https://cloud.google.com/iam/docs/service-accounts)
- [API Rate Limits](https://developers.google.com/docs/api/limits)

## Support

For issues or questions:
- Check existing [GitHub Issues](https://github.com/irsiksoftware/TalkSmith/issues)
- Open a new issue with tag `google-docs-integration`
- Include relevant error messages and configuration (redact credentials)
