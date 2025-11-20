# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Nothing yet

### Changed
- Nothing yet

### Fixed
- Nothing yet

## [0.1.0] - 2025-01-XX

### Added
- Initial project structure and documentation
- Centralized configuration system (`config/settings.ini`)
- Comprehensive test suite with pytest and CI/CD pipeline
- Structured JSON logging utility with metrics tracking and retry/backoff
- Export formats: TXT, SRT, VTT, JSON with validation
- CLI interface with export, batch, and demo commands
- WhisperX diarization with pyannote.audio integration
- Alternative no-token diarization (resemblyzer-based)
- PII redaction for emails, phones, SSNs, credit cards, IPs
- Model cache management with prefetch scripts
- Speaker post-processing (normalization and utterance merging)
- Outline generation with timestamped anchors and topic detection
- LLM-powered PRD/plan generation (Claude and GPT support)
- Google Docs API integration for plan publishing
- Google Drive sync using rclone (cross-platform)
- Docker (CUDA) support with docker-compose
- Python environment setup scripts (make_env.ps1/sh)
- GPU and CUDA verification scripts
- FFmpeg installation verification
- Recording consent template (docs/consent_template.md)
- Comprehensive documentation in docs/ directory

### Changed
- Python requirement: 3.10 or 3.11 (3.12 not yet supported)

### Fixed
- None yet (initial release)

### Security
- PII redaction implemented with whitelist support

## [0.0.1] - 2025-01-XX (Planning Phase)

### Added
- Project repository created
- Initial README with planned features and architecture
- Roadmap defined (P0, P1, P2 phases)

---

## Version History

- **0.1.0** - Current development version (Phase 1 mostly complete)
- **0.0.1** - Initial planning and documentation

---

## How to Update This Changelog

When adding new features or fixes:

1. **Add entries under [Unreleased]** section
2. **Use appropriate categories**:
   - `Added` for new features
   - `Changed` for changes in existing functionality
   - `Deprecated` for soon-to-be removed features
   - `Removed` for now removed features
   - `Fixed` for any bug fixes
   - `Security` for vulnerability fixes

3. **Use bullet points** with concise descriptions
4. **Link to issues/PRs** when applicable: `(#123)` or `([#123](link))`

### Example Entry

```markdown
## [Unreleased]

### Added
- Multi-GPU parallelism for faster transcription ([#42](https://github.com/DakotaIrsik/TalkSmith/issues/42))
- Benchmark suite for performance testing

### Fixed
- Audio preprocessing denoise filter not applying correctly ([#55](https://github.com/DakotaIrsik/TalkSmith/issues/55))
```

---

## Release Process

When cutting a new release:

1. **Move [Unreleased] items** to a new version section
2. **Add release date**: `## [0.2.0] - 2025-02-15`
3. **Update project version** in `pyproject.toml`
4. **Create git tag**: `git tag -a v0.2.0 -m "Release v0.2.0"`
5. **Push tag**: `git push origin v0.2.0`
6. **Create GitHub release** with changelog excerpt

---

## Links

- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
