# TalkSmith Testing Guide

Comprehensive testing documentation for contributors and developers.

## Quick Start

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all fast tests
make test

# Run with coverage
make coverage
```

## Test Philosophy

TalkSmith follows these testing principles:

1. **Comprehensive Coverage**: Aim for >90% code coverage on core modules
2. **Fast Feedback**: Unit tests should run in <5 seconds total
3. **Isolated Tests**: Each test should be independent and reproducible
4. **Realistic Scenarios**: Integration tests use realistic audio samples
5. **Clear Intent**: Test names clearly describe what is being tested

## Test Categories

### Unit Tests (`tests/unit/`)
Fast, isolated tests for individual functions and classes.

**Coverage Areas:**
- ✅ Configuration system (`test_config.py`) - Fully implemented
- ✅ Logging utility (`test_logger.py`) - Fully implemented
- ✅ Error handling (`test_error_handling.py`) - Framework ready
- ✅ Performance metrics (`test_performance.py`) - Framework ready
- 📋 Transcription logic (`test_transcribe.py`) - Placeholder for future implementation
- 📋 Diarization algorithms (`test_diarization.py`) - Placeholder for future implementation
- 📋 Export formats (`test_exports.py`) - Placeholder for future implementation
- 📋 GPU detection (`test_check_gpu.py`) - Placeholder for future implementation

**Run Command:**
```bash
pytest tests/unit -m unit
```

### Integration Tests (`tests/integration/`)
Tests for workflows spanning multiple modules.

**Coverage Areas:**
- 📋 End-to-end pipeline (`test_full_pipeline.py`) - Placeholder for future implementation
- 📋 CLI interface - Placeholder for future implementation
- 📋 Batch processing - Placeholder for future implementation
- 📋 Multi-GPU coordination - Placeholder for future implementation

**Run Command:**
```bash
pytest tests/integration -m integration
```

### Performance Tests
Tests that measure and validate performance characteristics.

**Metrics Tracked:**
- Real-Time Factor (RTF)
- Memory usage
- GPU utilization
- Throughput (files/hour)

**Run Command:**
```bash
pytest -m slow  # Performance tests are marked as slow
```

## Test Markers

Use pytest markers to categorize and select tests:

```python
@pytest.mark.unit          # Fast unit test
@pytest.mark.integration   # Integration test
@pytest.mark.slow          # Slow test (>5 seconds)
@pytest.mark.gpu           # Requires GPU hardware
@pytest.mark.e2e           # End-to-end test
```

### Running Specific Test Types

```bash
# Only unit tests, no GPU required
pytest -m "unit and not gpu"

# Only fast tests
pytest -m "not slow"

# All tests except GPU tests
pytest -m "not gpu"

# Only GPU tests (requires hardware)
pytest -m gpu
```

## Writing Tests

### Unit Test Template

```python
import pytest

@pytest.mark.unit
class TestMyFeature:
    """Tests for MyFeature functionality."""

    def test_basic_functionality(self):
        """Test basic feature works correctly."""
        # Arrange
        input_data = create_test_data()

        # Act
        result = my_feature(input_data)

        # Assert
        assert result.status == "success"
        assert len(result.items) > 0

    def test_error_handling(self):
        """Test feature handles errors gracefully."""
        with pytest.raises(ValueError, match="Invalid input"):
            my_feature(invalid_data)
```

### Using Fixtures

```python
@pytest.mark.unit
def test_with_fixtures(sample_segments, temp_dir):
    """Test using shared fixtures."""
    # Fixtures are automatically provided by pytest
    output_file = temp_dir / "output.json"
    process_segments(sample_segments, output_file)
    assert output_file.exists()
```

### Integration Test Template

```python
import pytest

@pytest.mark.integration
@pytest.mark.slow
class TestFullWorkflow:
    """Tests for complete workflows."""

    def test_transcribe_and_export(self, sample_audio_path, temp_dir):
        """Test complete transcription workflow."""
        # Run full pipeline
        result = run_pipeline(
            audio=sample_audio_path,
            output_dir=temp_dir,
            formats=["txt", "srt", "json"]
        )

        # Verify outputs
        assert result["status"] == "success"
        assert (temp_dir / "transcript.txt").exists()
        assert (temp_dir / "transcript.srt").exists()
        assert (temp_dir / "segments.json").exists()
```

## Test Fixtures

Common fixtures are available in `tests/conftest.py`:

### File Fixtures
- `temp_dir`: Temporary directory for test outputs
- `sample_audio_path`: Path to sample audio file
- `settings_ini`: Test configuration file

### Data Fixtures
- `sample_audio_data`: Synthetic audio data (numpy array)
- `sample_segments`: Mock transcription segments
- `mock_whisper_result`: Mock Whisper output

### Environment Fixtures
- `mock_gpu_available`: Simulates GPU available
- `mock_no_gpu`: Simulates no GPU

## Coverage Requirements

| Module | Target Coverage | Current |
|--------|----------------|---------|
| `pipeline/transcribe_fw.py` | >90% | TBD |
| `pipeline/diarize_whisperx.py` | >90% | TBD |
| `pipeline/preprocess.py` | >85% | TBD |
| `pipeline/export.py` | >95% | TBD |
| `cli/main.py` | >80% | TBD |

### Checking Coverage

```bash
# Generate coverage report
pytest --cov=pipeline --cov=cli --cov-report=html

# View report
make coverage-report
```

## Continuous Integration

Tests run automatically on:
- Every push to `main` or `develop`
- Every pull request
- Nightly builds (including slow tests)

### CI Test Matrix

| OS | Python | GPU Tests |
|----|--------|-----------|
| Ubuntu 22.04 | 3.10 | No |
| Ubuntu 22.04 | 3.11 | No |
| Windows 2022 | 3.10 | No |
| Windows 2022 | 3.11 | No |

GPU tests run separately on self-hosted runners with CUDA support.

## Test Data

### Generating Fixtures

```bash
# Generate synthetic test audio
python tests/fixtures/generate_fixtures.py
```

This creates:
- `sample_short.wav` - 5 seconds
- `sample_medium.wav` - 1 minute
- Expected output files for validation

### Real Audio Samples

For testing with real audio:
1. Place files in `tests/fixtures/`
2. Update `.gitignore` to exclude large files
3. Use Git LFS for version control

## Debugging Tests

### Running Single Test

```bash
# Run specific test
pytest tests/unit/test_transcribe_fw.py::TestTranscribeFW::test_model_initialization -v

# Run and stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Enter debugger on failure
pytest --pdb
```

### Debugging Output

```python
# Use capsys fixture to capture output
def test_with_output(capsys):
    print("Debug info")
    my_function()
    captured = capsys.readouterr()
    assert "expected" in captured.out
```

## Performance Benchmarking

### Running Benchmarks

```bash
# Run performance tests
pytest tests/unit/test_performance.py -v

# With detailed timing
pytest --durations=10
```

### Adding Benchmarks

Use `pytest-benchmark` for performance testing:

```python
def test_transcription_speed(benchmark):
    """Benchmark transcription speed."""
    result = benchmark(transcribe, audio_data)
    assert result is not None
```

## Best Practices

1. **Test Names**: Use descriptive names starting with `test_`
   - Good: `test_speaker_labels_normalized_correctly`
   - Bad: `test_1`, `test_speakers`

2. **Arrange-Act-Assert**: Structure tests clearly
   ```python
   # Arrange
   input_data = setup_test_data()
   # Act
   result = function_under_test(input_data)
   # Assert
   assert result.is_valid()
   ```

3. **One Concept Per Test**: Each test should verify one thing
   - Don't: Test multiple unrelated features in one test
   - Do: Split into multiple focused tests

4. **Avoid Test Interdependence**: Tests should run independently
   - Use fixtures, not global state
   - Clean up in teardown or use `temp_dir`

5. **Meaningful Assertions**: Use specific assertions
   - Good: `assert result.code == 200`
   - Bad: `assert result`

6. **Test Error Cases**: Don't just test happy paths
   - Invalid inputs
   - Edge cases
   - Error conditions

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure package is installed in development mode
pip install -e .
```

**Fixture Not Found**
- Check `conftest.py` exists
- Verify fixture name matches

**Tests Hang**
```bash
# Add timeout
pytest --timeout=30
```

**GPU Tests Fail**
```bash
# Skip GPU tests
pytest -m "not gpu"
```

## Contributing Tests

When submitting a PR:

1. ✅ Add tests for new features
2. ✅ Update tests for changed functionality
3. ✅ Ensure all tests pass: `make test`
4. ✅ Check coverage: `make coverage`
5. ✅ Run linting: `make lint`
6. ✅ Format code: `make format`

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)

## Questions?

- Open an issue on GitHub
- Check existing tests for examples
- Review `tests/README.md` for quick reference
