# TalkSmith - Google Drive Sync Script (Windows)
# Syncs transcription outputs to Google Drive using rclone

param(
    [switch]$DryRun,
    [switch]$Verbose,
    [switch]$Help
)

# Configuration
$RemoteName = if ($env:RCLONE_REMOTE_NAME) { $env:RCLONE_REMOTE_NAME } else { "gdrive" }
$LocalDir = if ($env:RCLONE_LOCAL_DIR) { $env:RCLONE_LOCAL_DIR } else { ".\data\outputs" }
$RemoteDir = if ($env:RCLONE_REMOTE_DIR) { $env:RCLONE_REMOTE_DIR } else { "TalkSmith/Transcripts" }

# Show help
if ($Help) {
    Write-Host "Usage: .\sync_to_drive.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -DryRun      Preview changes without uploading"
    Write-Host "  -Verbose     Show detailed output"
    Write-Host "  -Help        Show this help message"
    Write-Host ""
    Write-Host "Environment variables:"
    Write-Host "  RCLONE_REMOTE_NAME  Remote name (default: gdrive)"
    Write-Host "  RCLONE_LOCAL_DIR    Local directory (default: .\data\outputs)"
    Write-Host "  RCLONE_REMOTE_DIR   Remote directory (default: TalkSmith/Transcripts)"
    exit 0
}

# Check if rclone is installed
if (-not (Get-Command rclone -ErrorAction SilentlyContinue)) {
    Write-Error "Error: rclone is not installed"
    Write-Host "Download from: https://rclone.org/downloads/"
    exit 1
}

# Check if remote is configured
$remotes = rclone listremotes
if ($remotes -notmatch "^${RemoteName}:$") {
    Write-Error "Error: rclone remote '${RemoteName}' is not configured"
    Write-Host "Run: rclone config"
    exit 1
}

# Check if local directory exists
if (-not (Test-Path $LocalDir)) {
    Write-Error "Error: Local directory '$LocalDir' does not exist"
    exit 1
}

# Build rclone arguments
$rcloneArgs = @(
    "sync",
    $LocalDir,
    "${RemoteName}:${RemoteDir}",
    "--progress",
    "--exclude", ".DS_Store",
    "--exclude", "*.tmp",
    "--exclude", "*.part",
    "--exclude", ".cache/",
    "--exclude", "__pycache__/"
)

if ($DryRun) {
    Write-Host "Running in DRY-RUN mode (no changes will be made)"
    $rcloneArgs += "--dry-run"
}

if ($Verbose) {
    $rcloneArgs += "-v"
}

# Perform sync
Write-Host "Syncing: $LocalDir -> ${RemoteName}:${RemoteDir}"

& rclone @rcloneArgs

if ($LASTEXITCODE -eq 0) {
    if ($DryRun) {
        Write-Host ""
        Write-Host "Dry-run complete. No files were modified."
        Write-Host "Remove -DryRun to perform actual sync."
    } else {
        Write-Host ""
        Write-Host "Sync complete!"
    }
} else {
    Write-Error "Sync failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}
