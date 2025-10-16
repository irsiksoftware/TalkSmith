# Google Drive Sync

Sync your TalkSmith transcription outputs to Google Drive for backup or mobile access.

## Overview

TalkSmith includes scripts to automatically sync your transcription outputs to Google Drive using [rclone](https://rclone.org/). This enables:

- **Cloud backup** of all transcriptions
- **Mobile access** to transcripts from any device
- **Team sharing** of transcription outputs
- **Automated workflows** with scheduled syncs

## Prerequisites

### 1. Install rclone

#### Linux/macOS
```bash
curl https://rclone.org/install.sh | sudo bash
```

#### Windows
Download the installer from [rclone.org/downloads](https://rclone.org/downloads/)

Verify installation:
```bash
rclone version
```

### 2. Configure Google Drive Remote

Run the interactive configuration:
```bash
rclone config
```

Follow these steps:
1. Choose `n` for new remote
2. Name it `gdrive` (or your preferred name)
3. Choose `drive` for Google Drive
4. Follow OAuth2 authentication flow
5. Choose default options for remaining prompts

Test the connection:
```bash
rclone lsd gdrive:
```

You should see your Google Drive folders listed.

## Usage

### Basic Sync

#### Linux/macOS
```bash
./scripts/sync_to_drive.sh
```

#### Windows
```powershell
.\scripts\sync_to_drive.ps1
```

This syncs `./data/outputs/` to `gdrive:TalkSmith/Transcripts/`

### Dry-Run Mode

Preview what will be synced without making changes:

#### Linux/macOS
```bash
./scripts/sync_to_drive.sh --dry-run
```

#### Windows
```powershell
.\scripts\sync_to_drive.ps1 -DryRun
```

### Verbose Output

Show detailed sync progress:

#### Linux/macOS
```bash
./scripts/sync_to_drive.sh --verbose
```

#### Windows
```powershell
.\scripts\sync_to_drive.ps1 -Verbose
```

## Configuration

### Environment Variables

Customize sync behavior with environment variables:

```bash
# Remote name (default: gdrive)
export RCLONE_REMOTE_NAME=gdrive

# Local directory to sync (default: ./data/outputs)
export RCLONE_LOCAL_DIR=./data/outputs

# Remote directory path (default: TalkSmith/Transcripts)
export RCLONE_REMOTE_DIR=TalkSmith/Transcripts
```

### Excluded Files

The following patterns are automatically excluded from sync:
- `.DS_Store` (macOS metadata)
- `*.tmp` (temporary files)
- `*.part` (partial downloads)
- `.cache/` (cache directories)
- `__pycache__/` (Python cache)

## Automated Sync

### Linux/macOS (cron)

Add to your crontab to sync every 30 minutes:

```bash
crontab -e
```

Add this line:
```
*/30 * * * * cd /path/to/TalkSmith && ./scripts/sync_to_drive.sh >> /var/log/talksmith-sync.log 2>&1
```

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., every 30 minutes)
4. Set action: Run `powershell.exe`
5. Add arguments: `-File C:\path\to\TalkSmith\scripts\sync_to_drive.ps1`

## Verification

Check synced files on Google Drive:

```bash
rclone ls gdrive:TalkSmith/Transcripts
```

Compare local and remote:

```bash
rclone check ./data/outputs gdrive:TalkSmith/Transcripts
```

## Security Considerations

### Configuration File
rclone stores credentials in:
- Linux/macOS: `~/.config/rclone/rclone.conf`
- Windows: `%APPDATA%\rclone\rclone.conf`

**Keep this file secure!** It contains OAuth tokens.

### Service Accounts
For automated/headless deployments, use [service accounts](https://rclone.org/drive/#service-account-support):

```bash
rclone config create gdrive drive service_account_file /path/to/service-account.json
```

### Encryption
Enable encryption for sensitive data:

```bash
rclone config create gdrive-crypt crypt remote gdrive:TalkSmith/Transcripts
```

Then sync to the encrypted remote:
```bash
export RCLONE_REMOTE_NAME=gdrive-crypt
./scripts/sync_to_drive.sh
```

## Troubleshooting

### "Remote not found" error
- Verify remote name: `rclone listremotes`
- Reconfigure: `rclone config`

### Authentication expired
Refresh tokens:
```bash
rclone config reconnect gdrive:
```

### Slow uploads
Use `--transfers` flag for parallel uploads:
```bash
rclone sync ./data/outputs gdrive:TalkSmith/Transcripts --transfers 8
```

### Quota exceeded
Check Drive quota:
```bash
rclone about gdrive:
```

## Advanced Usage

### Watch Mode (Auto-sync on changes)

Linux/macOS with `inotifywait`:
```bash
while inotifywait -r -e modify,create,delete ./data/outputs; do
  ./scripts/sync_to_drive.sh
done
```

Windows with PowerShell:
```powershell
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = ".\data\outputs"
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true

Register-ObjectEvent $watcher "Created" -Action {
  .\scripts\sync_to_drive.ps1
}
```

### Sync Specific Formats
Only sync certain file types:
```bash
rclone sync ./data/outputs gdrive:TalkSmith/Transcripts \
  --include "*.txt" \
  --include "*.srt" \
  --progress
```

### Bidirectional Sync
Use `bisync` for two-way synchronization:
```bash
rclone bisync ./data/outputs gdrive:TalkSmith/Transcripts --resync
```

## Alternative: Direct Google Drive API

If you prefer not to use rclone, you can implement direct integration:

```python
# Using google-api-python-client
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

service = build('drive', 'v3', credentials=creds)
# Upload logic here
```

This requires OAuth2 credentials and more complex code, but eliminates the external dependency.

## Support

- rclone docs: https://rclone.org/drive/
- Google Drive API: https://developers.google.com/drive
- TalkSmith issues: https://github.com/irsiksoftware/TalkSmith/issues
