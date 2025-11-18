# Testing Quick Reference

## Run Tests

```bash
# All tests (fast)
pytest -m "not slow and not gpu"

# Unit tests only
pytest tests/unit -m unit

# Integration tests
pytest tests/integration -m integration

# With coverage
pytest --cov=pipeline --cov=cli --cov-report=html

# Parallel execution
pytest -n auto

# Stop on first failure
pytest -x

# Verbose output
pytest -v
```

## Using Makefile

```bash
make test              # Run fast tests
make test-unit         # Unit tests only
make coverage          # Generate coverage report
make lint              # Run linting
make format            # Format code
make clean             # Clean generated files
```

## Test Markers

```python
@pytest.mark.unit          # Fast unit test
@pytest.mark.integration   # Integration test
@pytest.mark.slow          # Slow test
@pytest.mark.gpu           # Requires GPU
```

## Common Fixtures

```python
def test_example(temp_dir, sample_audio_path, sample_segments):
    """Use common fixtures in tests."""
    pass
```

Available fixtures:

- `temp_dir` - Temporary directory
- `sample_audio_path` - Audio file path
- `sample_audio_data` - Numpy audio array
- `sample_segments` - Mock segments
- `mock_whisper_result` - Mock transcription
- `settings_ini` - Test config
- `mock_gpu_available` - Mock GPU present
- `mock_no_gpu` - Mock no GPU

## Writing Tests

```python
import pytest

@pytest.mark.unit
class TestMyFeature:
    def test_basic_functionality(self, temp_dir):
        """Test description."""
        # Arrange
        input_data = setup()

        # Act
        result = my_function(input_data)

        # Assert
        assert result is not None
```

## Coverage Goals

| Module | Target |
|--------|--------|
| pipeline | >90% |
| cli | >80% |
| Overall | >85% |

## CI/CD

Tests run automatically on:

- Push to main/develop
- Pull requests
- Multi-platform (Ubuntu, Windows)
- Python 3.10, 3.11

## Documentation

- `tests/README.md` - Test suite overview
- `TESTING.md` - Comprehensive guide
- `TEST_SUMMARY.md` - Infrastructure summary
