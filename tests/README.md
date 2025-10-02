# TalkSmith Test Suite

Comprehensive test suite for the TalkSmith transcription and diarization pipeline.

## Test Structure

```
tests/
├── conftest.py              # Shared pytest fixtures
├── unit/                    # Unit tests for individual modules
│   ├── test_transcribe_fw.py
│   ├── test_diarize_whisperx.py
│   ├── test_preprocess.py
│   ├── test_export.py
│   ├── test_postprocess_speakers.py
│   └── test_check_gpu.py
├── integration/             # Integration tests
│   ├── test_pipeline_e2e.py
│   └── test_cli.py
├── fixtures/                # Test data and fixtures
│   ├── generate_fixtures.py
│   └── README.md
└── utils/                   # Test utilities
    └── test_helpers.py
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test categories
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Exclude slow tests
pytest -m "not slow"

# GPU tests only (requires GPU)
pytest -m gpu
```

### Run with coverage
```bash
pytest --cov=pipeline --cov=cli --cov-report=html
```

### Run tests in parallel
```bash
pytest -n auto
```

## Test Markers

- `@pytest.mark.unit` - Fast unit tests for individual functions
- `@pytest.mark.integration` - Integration tests across modules
- `@pytest.mark.e2e` - End-to-end tests with real audio
- `@pytest.mark.slow` - Slow-running tests (excluded by default)
- `@pytest.mark.gpu` - Tests requiring GPU hardware

## Writing Tests

### Unit Test Example
```python
import pytest

@pytest.mark.unit
def test_speaker_normalization(sample_segments):
    """Test speaker label normalization."""
    # Arrange
    segments = sample_segments

    # Act
    normalized = normalize_speakers(segments)

    # Assert
    assert normalized[0]["speaker"] == "Speaker 1"
    assert normalized[1]["speaker"] == "Speaker 2"
```

### Integration Test Example
```python
import pytest

@pytest.mark.integration
@pytest.mark.slow
def test_full_pipeline(sample_audio_path, temp_dir):
    """Test complete transcription pipeline."""
    # Arrange
    input_file = sample_audio_path
    output_dir = temp_dir

    # Act
    result = run_pipeline(input_file, output_dir)

    # Assert
    assert result["status"] == "success"
    assert (output_dir / "transcript.txt").exists()
```

## Fixtures

Common fixtures are defined in `conftest.py`:

- `temp_dir` - Temporary directory for test files
- `sample_audio_path` - Path to sample audio file
- `sample_audio_data` - Synthetic audio data (numpy array)
- `sample_segments` - Mock transcription segments
- `mock_whisper_result` - Mock Whisper model output
- `settings_ini` - Test configuration file
- `mock_gpu_available` - Mock GPU availability
- `mock_no_gpu` - Mock no GPU available

## Test Coverage Goals

- **Unit tests:** >90% coverage of core modules
- **Integration tests:** All major workflows covered
- **E2E tests:** At least one complete pipeline test per export format

## CI/CD Integration

Tests are designed to run in CI environments:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pytest -m "not gpu and not slow" --cov
```

## Troubleshooting

### Tests fail with "No module named 'pipeline'"
Ensure you're running from the project root and have installed dependencies:
```bash
pip install -e .
pip install -r requirements-dev.txt
```

### GPU tests fail
GPU tests require CUDA-capable hardware. Skip with:
```bash
pytest -m "not gpu"
```

### Slow tests timeout
Increase timeout or skip slow tests:
```bash
pytest -m "not slow"
# or
pytest --timeout=300
```

## Contributing

When adding new features:
1. Write unit tests for individual functions
2. Add integration tests for workflows
3. Update fixtures if needed
4. Ensure tests pass: `pytest`
5. Check coverage: `pytest --cov`

Aim for:
- Clear test names describing what is tested
- Arrange-Act-Assert structure
- Appropriate markers (@pytest.mark.unit, etc.)
- Proper use of fixtures
- Good test isolation (no dependencies between tests)
