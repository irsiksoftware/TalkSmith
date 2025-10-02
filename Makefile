# Makefile for TalkSmith development tasks

.PHONY: help test test-unit test-integration test-all coverage lint format clean install-dev

help:
	@echo "TalkSmith Development Tasks"
	@echo "=========================="
	@echo "make install-dev    Install development dependencies"
	@echo "make test          Run all tests (excluding slow/gpu)"
	@echo "make test-unit     Run unit tests only"
	@echo "make test-integration  Run integration tests"
	@echo "make test-all      Run all tests including slow ones"
	@echo "make coverage      Run tests with coverage report"
	@echo "make lint          Run code quality checks"
	@echo "make format        Format code with black and isort"
	@echo "make clean         Clean generated files"

install-dev:
	pip install -r requirements-dev.txt
	pip install -e .

test:
	pytest -m "not slow and not gpu" -v

test-unit:
	pytest tests/unit -m "unit and not gpu" -v

test-integration:
	pytest tests/integration -m "integration and not slow and not gpu" -v

test-all:
	pytest -v

test-fast:
	pytest -m "not slow and not gpu" -x -v

coverage:
	pytest --cov=config --cov=pipeline --cov-report=html --cov-report=term-missing

coverage-report:
	@echo "Opening coverage report..."
	@python -m webbrowser htmlcov/index.html 2>/dev/null || xdg-open htmlcov/index.html 2>/dev/null || open htmlcov/index.html

lint:
	@echo "Running flake8..."
	flake8 config pipeline tests --max-line-length=100
	@echo "Running mypy..."
	mypy config pipeline --ignore-missing-imports
	@echo "Checking with black..."
	black --check .
	@echo "Checking with isort..."
	isort --check-only .

format:
	@echo "Formatting with black..."
	black .
	@echo "Sorting imports with isort..."
	isort .

clean:
	@echo "Cleaning generated files..."
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Clean complete!"

# Generate test fixtures
fixtures:
	python tests/fixtures/generate_fixtures.py

# Run quick smoke tests
smoke:
	pytest -m "unit" --maxfail=1 -x

# Run tests in parallel
test-parallel:
	pytest -n auto -m "not slow and not gpu"
