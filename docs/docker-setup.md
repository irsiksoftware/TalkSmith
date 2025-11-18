# Docker CUDA Setup Guide

This guide covers Docker setup for TalkSmith with CUDA GPU acceleration support.

## Overview

TalkSmith includes Docker and Docker Compose configurations for:

- **Reproducible GPU environments** across development machines
- **CUDA-enabled containers** for GPU-accelerated transcription
- **Multi-GPU support** for parallel processing
- **Isolated dependencies** without affecting host system

## Prerequisites

### Required

- **Docker Engine** 20.10+ ([Install Guide](https://docs.docker.com/engine/install/))
- **NVIDIA GPU** with CUDA support
- **nvidia-container-toolkit** or nvidia-docker2 ([Install Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html))

### System Requirements

- **Linux:** Ubuntu 18.04+, Debian 10+, CentOS 7+, or compatible
- **GPU:** NVIDIA GPU with Compute Capability 3.5+ (GTX 700 series or newer)
- **Driver:** NVIDIA Driver 450.80.02+ (for CUDA 11.x support)
- **RAM:** 8GB+ recommended (16GB+ for large models)
- **Disk:** 20GB+ for Docker images and model cache

### Windows/macOS Note

Docker CUDA support is **Linux-only**. For Windows/macOS:

- Use **WSL2** with Docker Desktop on Windows ([WSL2 + GPU Guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html))
- Use **native installation** or cloud instances on macOS

## Installation

### 1. Install NVIDIA Container Toolkit

#### Ubuntu/Debian

```bash
# Add NVIDIA GPG key
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# Add repository
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Restart Docker
sudo systemctl restart docker
```

#### CentOS/RHEL

```bash
# Add repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/nvidia-container-toolkit.repo | \
    sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

# Install toolkit
sudo yum install -y nvidia-container-toolkit

# Restart Docker
sudo systemctl restart docker
```

### 2. Verify GPU Access

```bash
# Test NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Expected: nvidia-smi output showing your GPU(s)
```

### 3. Clone TalkSmith Repository

```bash
git clone https://github.com/DakotaIrsik/TalkSmith.git
cd TalkSmith
```

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Build and start container
docker compose up -d

# Verify container is running
docker compose ps

# Run CLI commands
docker compose run --rm talksmith python cli/main.py --help

# Example: Export segments
docker compose run --rm talksmith python cli/main.py export \
    --input /workspace/data/samples/test-segments.json \
    --formats txt,srt,json \
    --output-dir /workspace/data/outputs

# Stop container
docker compose down
```

### Option 2: Docker CLI

```bash
# Build image
docker build -t talksmith:cuda -f Dockerfile.cuda .

# Run interactively
docker run --rm -it --gpus all \
    -v $(pwd)/data:/workspace/data \
    -v $(pwd)/.cache:/workspace/.cache \
    talksmith:cuda bash

# Run CLI command
docker run --rm --gpus all \
    -v $(pwd)/data:/workspace/data \
    talksmith:cuda python cli/main.py --help
```

## Configuration

### Docker Compose Configuration

The `docker-compose.yml` file supports customization:

```yaml
services:
  talksmith:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all  # Change to '1' or '2' to limit GPU count
              capabilities: [gpu]

    environment:
      # Override settings via environment variables
      TALKSMITH_MODELS_WHISPER_MODEL: "large-v3"
      TALKSMITH_LOGGING_LEVEL: "INFO"

    volumes:
      # Mount local directories
      - ./data:/workspace/data
      - ./.cache:/workspace/.cache
      # Optional: Mount custom config
      - ./my-settings.ini:/workspace/config/settings.ini
```

### GPU Selection

#### All GPUs (default)

```yaml
count: all  # Use all available GPUs
```

#### Specific GPU Count

```yaml
count: 1  # Use only 1 GPU
```

#### Specific GPU IDs

```yaml
device_ids: ['0']  # Use only GPU 0
```

#### Multiple Specific GPUs

```yaml
device_ids: ['0', '1']  # Use GPUs 0 and 1
```

### Memory Limits

Add memory constraints to prevent OOM:

```yaml
services:
  talksmith:
    deploy:
      resources:
        limits:
          memory: 16G  # Limit to 16GB RAM
        reservations:
          memory: 8G   # Reserve 8GB RAM
```

## Usage Examples

### Prefetch Models

```bash
# Download models for offline use
docker compose run --rm talksmith \
    ./scripts/prefetch_models.sh medium.en large-v3
```

### Export Segments

```bash
# Export to multiple formats
docker compose run --rm talksmith python cli/main.py export \
    --input /workspace/data/segments.json \
    --formats txt,srt,vtt,json \
    --output-dir /workspace/data/exports
```

### Batch Processing

```bash
# Process directory of segment files
docker compose run --rm talksmith python cli/main.py batch \
    --input-dir /workspace/data/segments \
    --formats srt,json \
    --output-dir /workspace/data/transcripts
```

### Speaker Post-Processing

```bash
# Normalize speakers and merge short utterances
docker compose run --rm talksmith python pipeline/postprocess_speakers.py \
    /workspace/data/segments.json \
    -o /workspace/data/processed.json \
    --min-utterance-ms 1000
```

### Generate Outlines

```bash
# Create timestamped outline
docker compose run --rm talksmith python pipeline/outline_from_segments.py \
    /workspace/data/segments.json \
    -o /workspace/data/outline.md \
    --title "Meeting Notes" \
    --interval 60
```

### Interactive Shell

```bash
# Start interactive bash session
docker compose run --rm talksmith bash

# Inside container:
python cli/main.py --help
pytest tests/ -v
python -c "import torch; print(torch.cuda.is_available())"
```

## Volumes and Data

### Default Volumes

```
./data       →  /workspace/data       (inputs/outputs)
./.cache     →  /workspace/.cache     (model cache)
```

### Custom Volume Mounts

Add to `docker-compose.yml`:

```yaml
volumes:
  - ./my-audio:/workspace/audio:ro  # Read-only audio files
  - ./my-outputs:/workspace/outputs # Writable output directory
```

## Troubleshooting

### GPU Not Detected

**Symptom:** `RuntimeError: CUDA not available` or `nvidia-smi` fails

**Solutions:**

```bash
# 1. Verify NVIDIA driver
nvidia-smi

# 2. Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# 3. Check nvidia-container-toolkit
sudo systemctl status nvidia-container-toolkit

# 4. Restart Docker daemon
sudo systemctl restart docker

# 5. Rebuild with --no-cache
docker compose build --no-cache
```

### Out of Memory (OOM)

**Symptom:** Container crashes or `CUDA out of memory` errors

**Solutions:**

```bash
# 1. Use smaller model
docker compose run -e TALKSMITH_MODELS_WHISPER_MODEL=medium.en talksmith ...

# 2. Limit GPU memory per process
docker compose run -e CUDA_VISIBLE_DEVICES=0 talksmith ...

# 3. Add memory limits to docker-compose.yml (see Configuration section)

# 4. Process files sequentially instead of in parallel
```

### Permission Errors

**Symptom:** Cannot write to mounted volumes

**Solutions:**

```bash
# 1. Fix ownership of mounted directories
sudo chown -R $USER:$USER ./data ./.cache

# 2. Run container with current user
docker compose run --user $(id -u):$(id -g) talksmith ...

# 3. Add user mapping to docker-compose.yml
```

Update `docker-compose.yml`:

```yaml
services:
  talksmith:
    user: "${UID:-1000}:${GID:-1000}"
```

### Slow Build Times

**Solutions:**

```bash
# 1. Use BuildKit for parallel builds
DOCKER_BUILDKIT=1 docker compose build

# 2. Leverage build cache
docker compose build  # Subsequent builds are faster

# 3. Pull pre-built base images
docker pull nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04
```

### Network Issues

**Symptom:** Cannot download models or packages

**Solutions:**

```bash
# 1. Use host network for troubleshooting
docker run --rm --gpus all --network host talksmith:cuda ...

# 2. Configure DNS
docker run --rm --gpus all --dns 8.8.8.8 talksmith:cuda ...

# 3. Use proxy if behind firewall
docker build --build-arg HTTP_PROXY=http://proxy:port -f Dockerfile.cuda .
```

## Advanced Configuration

### Custom CUDA Version

Modify `Dockerfile.cuda`:

```dockerfile
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04
# Update CUDA version as needed
```

### Multiple Compose Profiles

Create `docker-compose.override.yml` for development:

```yaml
services:
  talksmith:
    volumes:
      - .:/workspace:rw  # Mount entire codebase for development
    command: /bin/bash  # Start with shell
    stdin_open: true
    tty: true
```

Run: `docker compose -f docker-compose.yml -f docker-compose.override.yml up`

### CI/CD Integration

```bash
# Build in CI
docker build --cache-from talksmith:cuda -f Dockerfile.cuda -t talksmith:cuda .

# Run tests
docker run --rm talksmith:cuda pytest tests/

# Push to registry
docker tag talksmith:cuda myregistry/talksmith:latest
docker push myregistry/talksmith:latest
```

## Performance Tips

1. **Use volume mounts** instead of copying files into container
2. **Prefetch models** once and reuse cache: `./scripts/prefetch_models.sh`
3. **Limit GPU count** if running multiple containers: `count: 1`
4. **Use smaller models** for development: `medium.en` instead of `large-v3`
5. **Enable BuildKit** for faster builds: `export DOCKER_BUILDKIT=1`

## Security Considerations

1. **Run as non-root user** in production
2. **Limit container capabilities** using security profiles
3. **Scan images** for vulnerabilities: `docker scan talksmith:cuda`
4. **Use read-only volumes** where possible: `-v ./data:/workspace/data:ro`
5. **Keep base images updated** regularly

## Cleanup

```bash
# Stop and remove containers
docker compose down

# Remove volumes
docker compose down -v

# Remove images
docker rmi talksmith:cuda

# Full cleanup (careful!)
docker system prune -a --volumes
```

## Resources

- [NVIDIA Container Toolkit Docs](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/)
- [Docker GPU Support](https://docs.docker.com/config/containers/resource_constraints/#gpu)
- [CUDA Compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/)
- [Docker Compose GPU](https://docs.docker.com/compose/gpu-support/)

## Testing Docker Setup

Run the test suite to verify everything works:

```bash
# Unit tests (no GPU required)
docker compose run --rm talksmith pytest tests/unit -v

# Integration tests (may require GPU)
docker compose run --rm talksmith pytest tests/integration -v

# Check GPU access
docker compose run --rm talksmith python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')"
```

---

**Next Steps:**

1. Follow [Quick Start](#quick-start) to get running
2. Review [Usage Examples](#usage-examples) for common workflows
3. Customize [Configuration](#configuration) for your environment
4. See [Troubleshooting](#troubleshooting) if you encounter issues

For general TalkSmith usage, see the main [README](../README.md).
