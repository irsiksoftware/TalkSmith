# TalkSmith Decision Log

This document records key architectural and technical decisions made during the development of TalkSmith.

## Model Selection and Version Pinning

**Date:** 2025-10-02
**Status:** Implemented
**Decision Makers:** Development Team

### Context

TalkSmith requires stable, reproducible transcription and diarization results. Model versions can change over time, and newer versions may introduce breaking changes or different accuracy characteristics. We need to pin specific model versions and provide utilities to prefetch them for offline use.

### Decision

We have standardized on the following models with version pinning:

#### Whisper Models (via faster-whisper)

**Provider:** OpenAI Whisper, optimized via CTranslate2 (faster-whisper library)

**Recommended Models:**

- **Default:** `large-v3` - Best accuracy for production use
- **Fast:** `medium.en` - Good balance of speed and accuracy for English-only content
- **Lightweight:** `small.en` - For resource-constrained environments

**Available Model Sizes:**

| Model | Parameters | English-only | Disk Size | VRAM (FP16) | Use Case |
|-------|-----------|--------------|-----------|-------------|----------|
| `tiny` | 39M | No | ~75 MB | ~1 GB | Testing, very fast transcription |
| `tiny.en` | 39M | Yes | ~75 MB | ~1 GB | Testing, English-only fast transcription |
| `base` | 74M | No | ~150 MB | ~1 GB | Lightweight, multi-language |
| `base.en` | 74M | Yes | ~150 MB | ~1 GB | Lightweight, English-only |
| `small` | 244M | No | ~500 MB | ~2 GB | Good accuracy, faster than medium |
| `small.en` | 244M | Yes | ~500 MB | ~2 GB | Good accuracy, English-only |
| `medium` | 769M | No | ~1.5 GB | ~5 GB | High accuracy, multi-language |
| `medium.en` | 769M | Yes | ~1.5 GB | ~5 GB | High accuracy, English-only |
| `large-v2` | 1550M | No | ~3 GB | ~10 GB | Highest accuracy, older version |
| `large-v3` | 1550M | No | ~3 GB | ~10 GB | **Highest accuracy, latest stable** |

**Model Selection Guidelines:**

1. **For English-only content:** Use `.en` models (faster, often more accurate for English)
2. **For multi-language content:** Use non-`.en` models
3. **For production/critical work:** Use `large-v3` or `medium.en`
4. **For rapid iteration/testing:** Use `small.en` or `base.en`
5. **For batch processing:** Balance between accuracy needs and throughput

#### Diarization Models (via pyannote.audio)

**Provider:** pyannote.audio (Hervé Bredin)

**Selected Model:** `pyannote/speaker-diarization-3.1`

**Version:** 3.1 (latest stable as of 2025-10-02)

**Requirements:**

- HuggingFace account and token
- Acceptance of model terms at: <https://huggingface.co/pyannote/speaker-diarization-3.1>
- Size: ~100 MB

**Rationale:**

- State-of-the-art speaker diarization accuracy
- Active maintenance and community support
- Compatible with WhisperX integration
- Proven performance on multi-speaker scenarios

### Rationale for Version Pinning

1. **Reproducibility:** Ensures consistent results across different environments and time periods
2. **Stability:** Prevents unexpected breaking changes from upstream model updates
3. **Offline Capability:** Prefetched models enable fully offline transcription
4. **Performance Predictability:** Known performance characteristics for capacity planning
5. **Testing Reliability:** Stable models produce consistent test results

### Cache Management

**Cache Directory:** `.cache/` (configurable via `settings.ini`)

**Environment Variables:**

- `HF_HOME`: HuggingFace cache directory
- `TRANSFORMERS_CACHE`: Transformers library cache directory
- `TALKSMITH_PATHS_CACHE_DIR`: TalkSmith-specific cache override

**Prefetch Scripts:**

- Windows: `scripts/prefetch_models.ps1`
- Linux/macOS: `scripts/prefetch_models.sh`

**Features:**

- Selective model download (specify sizes)
- Optional diarization model download
- HuggingFace token support
- Disk space estimates
- Cache directory customization

### Usage Examples

```powershell
# Windows: Download default models (medium.en, large-v3)
.\scripts\prefetch_models.ps1

# Windows: Download specific models only
.\scripts\prefetch_models.ps1 -Sizes "medium.en,large-v3" -SkipDiarization

# Windows: Download with HuggingFace token
.\scripts\prefetch_models.ps1 -HfToken "hf_xxxxx"

# Windows: Custom cache directory
.\scripts\prefetch_models.ps1 -CacheDir "D:\Models"
```

```bash
# Linux/macOS: Download default models
./scripts/prefetch_models.sh

# Linux/macOS: Download specific models only
./scripts/prefetch_models.sh --sizes "medium.en,large-v3" --skip-diarization

# Linux/macOS: Download with HuggingFace token
./scripts/prefetch_models.sh --hf-token "hf_xxxxx"

# Linux/macOS: Custom cache directory
./scripts/prefetch_models.sh --cache-dir "/mnt/models"
```

### Future Considerations

1. **Model Updates:** Monitor for new Whisper releases (v4, etc.) and pyannote updates
2. **Performance Benchmarks:** Maintain benchmark suite comparing model versions
3. **Storage Optimization:** Consider model quantization (int8) for reduced disk/memory usage
4. **Alternative Models:** Evaluate alternatives like Distil-Whisper for faster inference
5. **Fine-tuning:** Consider domain-specific fine-tuning for specialized vocabulary

### Related Issues

- Issue #22: Model cache management and version pinning
- Issue #18: Tests (unit + end-to-end sample)

### References

- faster-whisper: <https://github.com/SYSTRAN/faster-whisper>
- OpenAI Whisper: <https://github.com/openai/whisper>
- pyannote.audio: <https://github.com/pyannote/pyannote-audio>
- CTranslate2: <https://github.com/OpenNMT/CTranslate2>

---

## Future Decision Topics

Topics to be documented as decisions are made:

- Audio preprocessing pipeline choices
- Multi-GPU parallelization strategy
- Export format standards
- PII redaction approach
- Batch processing architecture
- Testing strategy and coverage goals
- Docker image optimization
- CI/CD pipeline design
