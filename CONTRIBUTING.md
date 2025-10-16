# Contributing to TalkSmith

Thank you for your interest in contributing to TalkSmith! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## Getting Started

### Prerequisites

- Python 3.10 or 3.11
- NVIDIA GPU with CUDA support (recommended) or CPU
- FFmpeg installed on your system
- Git for version control

### Setting Up Development Environment

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/TalkSmith.git
   cd TalkSmith
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv

   # Windows
   .\venv\Scripts\activate

   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Run tests to verify setup:**
   ```bash
   pytest
   ```

## Development Workflow

### Branching Strategy

- `main` - Stable production branch
- `feat/<issue-number>-<description>` - Feature branches
- `fix/<issue-number>-<description>` - Bug fix branches
- `docs/<description>` - Documentation updates

### Working on an Issue

1. **Find or create an issue:**
   - Check existing [GitHub Issues](https://github.com/DakotaIrsik/TalkSmith/issues)
   - Comment on the issue to claim it
   - For new features, open an issue for discussion first

2. **Create a feature branch:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feat/<issue-number>-short-description
   ```

3. **Make your changes:**
   - Write clean, documented code
   - Follow coding standards (see below)
   - Add tests for new functionality
   - Update documentation as needed

4. **Test your changes:**
   ```bash
   # Run tests
   pytest

   # Run specific test file
   pytest tests/test_config.py

   # Run with coverage
   pytest --cov=. --cov-report=html
   ```

5. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: Add feature description (#issue-number)"
   ```

   **Commit Message Format:**
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `test:` - Adding or updating tests
   - `refactor:` - Code refactoring
   - `chore:` - Maintenance tasks

## Pull Request Process

1. **Push your branch:**
   ```bash
   git push origin feat/<issue-number>-description
   ```

2. **Create a Pull Request:**
   - Go to the GitHub repository
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template with:
     - Clear description of changes
     - Related issue number
     - Testing performed
     - Screenshots/examples if applicable

3. **PR Requirements:**
   - [ ] All tests pass
   - [ ] Code follows style guidelines
   - [ ] Documentation updated if needed
   - [ ] Commit messages follow conventions
   - [ ] PR description is clear and complete
   - [ ] At least one approval from CODEOWNERS

4. **Code Review:**
   - Address reviewer feedback promptly
   - Push additional commits to the same branch
   - Request re-review after changes

5. **Merging:**
   - PRs will be merged by maintainers after approval
   - Squash and merge is preferred for feature branches

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use meaningful variable and function names

### Code Quality

```python
# Good example
def transcribe_audio(
    audio_path: Path,
    model_size: str = "large-v3",
    device: str = "auto"
) -> dict:
    """
    Transcribe audio file using Whisper model.

    Args:
        audio_path: Path to input audio file
        model_size: Whisper model size
        device: Device to use (auto, cuda, cpu)

    Returns:
        Dictionary containing transcription results
    """
    # Implementation
    pass
```

### Formatting

Use tools to maintain code quality:

```bash
# Format code with black (if configured)
black .

# Sort imports with isort (if configured)
isort .

# Lint with flake8 (if configured)
flake8 .
```

## Testing

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names
- Aim for high code coverage

```python
# tests/test_transcribe.py
import pytest
from pathlib import Path

def test_transcribe_audio_success():
    """Test successful audio transcription."""
    # Arrange
    audio_path = Path("tests/fixtures/sample.wav")

    # Act
    result = transcribe_audio(audio_path)

    # Assert
    assert result["status"] == "success"
    assert "text" in result
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_config.py::test_load_config

# Run with coverage
pytest --cov=. --cov-report=html
```

## Documentation

### Code Documentation

- Add docstrings to all functions, classes, and modules
- Use Google-style docstrings
- Document parameters, return values, and exceptions

### README and Docs

- Update README.md for user-facing changes
- Add examples to demonstrate new features
- Update docs/ for detailed documentation

### Configuration

- Document new configuration options in `docs/configuration.md`
- Update `config/settings.ini` with sensible defaults
- Add examples in comments

## Questions and Support

- **Questions:** Open a [GitHub Discussion](https://github.com/DakotaIrsik/TalkSmith/discussions)
- **Bugs:** File an [Issue](https://github.com/DakotaIrsik/TalkSmith/issues)
- **Features:** Propose via [Issue](https://github.com/DakotaIrsik/TalkSmith/issues) for discussion

## Recognition

Contributors will be recognized in:
- README acknowledgments
- Release notes
- Git commit history

Thank you for contributing to TalkSmith!
