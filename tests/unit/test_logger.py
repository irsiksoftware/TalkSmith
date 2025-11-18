"""
Unit tests for pipeline.logger module.
"""

import json
import logging
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pipeline.logger import (
    BatchLogSummary,
    JSONFormatter,
    TalkSmithLogger,
    TransientError,
    get_logger,
    retry_operation,
    with_retry,
)


class TestJSONFormatter:
    """Test JSON formatter."""

    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["logger"] == "test"
        assert "timestamp" in log_data

    def test_format_with_custom_fields(self):
        """Test formatting with custom fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        # Add custom fields
        record.custom_field = "custom_value"
        record.metrics = {"rtf": 0.12}

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["custom_field"] == "custom_value"
        assert log_data["metrics"] == {"rtf": 0.12}

    def test_format_with_exception(self):
        """Test formatting with exception info."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        log_data = json.loads(result)

        assert "exception" in log_data
        assert "ValueError" in log_data["exception"]
        assert "Test error" in log_data["exception"]


class TestTalkSmithLogger:
    """Test TalkSmithLogger class."""

    def test_logger_creation(self):
        """Test basic logger creation."""
        logger = TalkSmithLogger(name="test")
        assert logger.logger is not None
        assert logger.slug is None

    def test_logger_with_slug(self):
        """Test logger with slug."""
        logger = TalkSmithLogger(name="test-slug-logger", slug="test-slug")
        assert logger.slug == "test-slug"

        # Close handlers
        for handler in logger.logger.handlers[:]:
            handler.close()
            logger.logger.removeHandler(handler)

    def test_log_methods(self, caplog):
        """Test various log methods."""
        logger = TalkSmithLogger(name="test", console_output=True, log_format="text")

        with caplog.at_level(logging.INFO):
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

        # Check log records
        assert "Info message" in caplog.text
        assert "Warning message" in caplog.text
        assert "Error message" in caplog.text

    def test_log_metrics(self):
        """Test metrics logging."""
        logger = TalkSmithLogger(name="test")

        with patch.object(logger.logger, "log") as mock_log:
            metrics = {"rtf": 0.12, "duration": 3600}
            logger.log_metrics(metrics)

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert "metrics" in call_args[1]["extra"]
            assert call_args[1]["extra"]["metrics"] == metrics

    def test_log_start_and_complete(self):
        """Test operation start and complete logging."""
        logger = TalkSmithLogger(name="test")

        with patch.object(logger.logger, "info") as mock_info:
            logger.log_start("transcription", audio_file="test.wav")

            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert call_args[1]["extra"]["operation"] == "transcription"
            assert call_args[1]["extra"]["stage"] == "start"

        with patch.object(logger.logger, "info") as mock_info:
            logger.log_complete("transcription", duration=120.5)

            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert call_args[1]["extra"]["operation"] == "transcription"
            assert call_args[1]["extra"]["stage"] == "complete"
            assert call_args[1]["extra"]["duration_seconds"] == 120.5

    def test_log_error_exit(self):
        """Test error exit logging."""
        logger = TalkSmithLogger(name="test")

        with patch.object(logger.logger, "error") as mock_error:
            exit_code = logger.log_error_exit("Fatal error", exit_code=2)

            assert exit_code == 2
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            assert call_args[1]["extra"]["exit_code"] == 2

    def test_json_format_logging(self, capsys):
        """Test JSON format output."""
        logger = TalkSmithLogger(name="test", console_output=True, log_format="json")

        logger.info("Test JSON logging", custom_field="value")

        captured = capsys.readouterr()
        output = captured.out + captured.err

        # Should contain JSON
        if output.strip():
            # Try to parse as JSON
            for line in output.strip().split("\n"):
                if line.strip():
                    data = json.loads(line)
                    if "Test JSON logging" in data.get("message", ""):
                        assert data["level"] == "INFO"
                        break


class TestGetLogger:
    """Test get_logger factory function."""

    def test_get_logger_default(self):
        """Test get_logger with defaults."""
        logger = get_logger("test")
        assert isinstance(logger, TalkSmithLogger)
        assert logger.logger.name == "test"

    def test_get_logger_with_slug(self):
        """Test get_logger with slug."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("pipeline.logger.get_config") as mock_config:
                config_mock = MagicMock()
                config_mock.get.side_effect = lambda section, key, fallback=None: {
                    ("Logging", "level"): "INFO",
                    ("Logging", "format"): "json",
                    ("Logging", "console_output"): "true",
                    ("Logging", "log_dir"): f"{tmpdir}/{{slug}}/logs",
                }.get((section, key), fallback)
                config_mock.get_bool.return_value = True
                mock_config.return_value = config_mock

                logger = get_logger("test", slug="my-file")
                assert logger.slug == "my-file"

    def test_get_logger_format_override(self):
        """Test get_logger with format override."""
        logger = get_logger("test", log_format="text")
        assert logger.log_format == "text"


class TestBatchLogSummary:
    """Test BatchLogSummary class."""

    def test_record_success(self):
        """Test recording successful operations."""
        logger = TalkSmithLogger(name="test")
        summary = BatchLogSummary(logger)

        summary.record_success("file1.wav")
        summary.record_success("file2.wav")

        assert summary.total == 2
        assert summary.successful == 2
        assert summary.failed == 0

    def test_record_failure(self):
        """Test recording failed operations."""
        logger = TalkSmithLogger(name="test")
        summary = BatchLogSummary(logger)

        summary.record_failure("file1.wav", "File not found")
        summary.record_success("file2.wav")

        assert summary.total == 2
        assert summary.successful == 1
        assert summary.failed == 1
        assert len(summary.errors) == 1
        assert summary.errors[0]["item"] == "file1.wav"

    def test_get_exit_code_success(self):
        """Test exit code for all successful."""
        logger = TalkSmithLogger(name="test")
        summary = BatchLogSummary(logger)

        summary.record_success("file1.wav")
        summary.record_success("file2.wav")

        assert summary.get_exit_code() == 0

    def test_get_exit_code_failure(self):
        """Test exit code with failures."""
        logger = TalkSmithLogger(name="test")
        summary = BatchLogSummary(logger)

        summary.record_success("file1.wav")
        summary.record_failure("file2.wav", "Error")

        assert summary.get_exit_code() == 1

    def test_print_summary(self, caplog):
        """Test print summary output."""
        logger = TalkSmithLogger(name="test", log_format="text")
        summary = BatchLogSummary(logger)

        summary.record_success("file1.wav")
        summary.record_success("file2.wav")
        summary.record_failure("file3.wav", "Processing error")

        with caplog.at_level(logging.INFO):
            summary.print_summary()

        assert "Batch complete" in caplog.text or "2/3 successful" in caplog.text

    def test_empty_summary(self):
        """Test summary with no operations."""
        logger = TalkSmithLogger(name="test")
        summary = BatchLogSummary(logger)

        assert summary.total == 0
        assert summary.get_exit_code() == 0


@pytest.mark.integration
class TestLoggerIntegration:
    """Integration tests for logger."""

    def test_full_logging_workflow(self, caplog):
        """Test complete logging workflow."""
        logger = get_logger("test-integration")

        with caplog.at_level(logging.INFO):
            logger.log_start("operation", file="test.wav")
            logger.info("Processing", progress=50)
            logger.log_complete("operation", duration=10.5)

        # Verify log messages were captured
        assert "Starting operation" in caplog.text
        assert "Processing" in caplog.text
        assert "Completed operation" in caplog.text

        # Close handlers
        for handler in logger.logger.handlers[:]:
            handler.close()
            logger.logger.removeHandler(handler)

    def test_batch_summary_integration(self):
        """Test batch summary integration."""
        logger = get_logger("test")
        summary = BatchLogSummary(logger)

        # Simulate batch processing
        files = ["file1.wav", "file2.wav", "file3.wav", "file4.wav"]
        for i, file in enumerate(files):
            if i == 2:  # Simulate failure on third file
                summary.record_failure(file, "Processing error")
            else:
                summary.record_success(file)

        summary.print_summary()

        assert summary.total == 4
        assert summary.successful == 3
        assert summary.failed == 1
        assert summary.get_exit_code() == 1


class TestRetryMechanism:
    """Test retry and backoff functionality."""

    def test_with_retry_decorator_success(self):
        """Test retry decorator with successful operation."""
        logger = TalkSmithLogger(name="test")
        call_count = {"count": 0}

        @with_retry(max_attempts=3, logger=logger)
        def operation():
            call_count["count"] += 1
            return "success"

        result = operation()
        assert result == "success"
        assert call_count["count"] == 1

    def test_with_retry_decorator_transient_error(self):
        """Test retry decorator with transient errors."""
        logger = TalkSmithLogger(name="test")
        call_count = {"count": 0}

        @with_retry(max_attempts=3, initial_delay=0.01, logger=logger)
        def operation():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise TransientError("Temporary failure")
            return "success"

        result = operation()
        assert result == "success"
        assert call_count["count"] == 3

    def test_with_retry_decorator_permanent_failure(self):
        """Test retry decorator with permanent failure."""
        logger = TalkSmithLogger(name="test")
        call_count = {"count": 0}

        @with_retry(max_attempts=3, initial_delay=0.01, logger=logger)
        def operation():
            call_count["count"] += 1
            raise TransientError("Permanent failure")

        with pytest.raises(TransientError):
            operation()

        assert call_count["count"] == 3

    def test_with_retry_non_transient_error(self):
        """Test retry decorator doesn't retry non-transient errors."""
        logger = TalkSmithLogger(name="test")
        call_count = {"count": 0}

        @with_retry(max_attempts=3, logger=logger)
        def operation():
            call_count["count"] += 1
            raise ValueError("Non-transient error")

        with pytest.raises(ValueError):
            operation()

        # Should fail immediately without retry
        assert call_count["count"] == 1

    def test_with_retry_custom_exceptions(self):
        """Test retry with custom exception types."""
        logger = TalkSmithLogger(name="test")
        call_count = {"count": 0}

        class CustomError(Exception):
            pass

        @with_retry(
            max_attempts=3,
            initial_delay=0.01,
            transient_exceptions=(CustomError,),
            logger=logger,
        )
        def operation():
            call_count["count"] += 1
            if call_count["count"] < 2:
                raise CustomError("Custom error")
            return "success"

        result = operation()
        assert result == "success"
        assert call_count["count"] == 2

    def test_retry_operation_function(self):
        """Test retry_operation function."""
        logger = TalkSmithLogger(name="test")
        call_count = {"count": 0}

        def operation():
            call_count["count"] += 1
            if call_count["count"] < 2:
                raise TransientError("Temporary failure")
            return "success"

        result = retry_operation(operation, max_attempts=3, initial_delay=0.01, logger=logger)

        assert result == "success"
        assert call_count["count"] == 2

    def test_retry_operation_with_lambda(self):
        """Test retry_operation with lambda."""
        logger = TalkSmithLogger(name="test")
        call_count = {"count": 0}

        def increment_and_check():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise ConnectionError("Connection failed")
            return call_count["count"]

        result = retry_operation(
            lambda: increment_and_check(),
            max_attempts=5,
            initial_delay=0.01,
            logger=logger,
            operation_name="test_connection",
        )

        assert result == 3
        assert call_count["count"] == 3

    def test_retry_backoff_timing(self):
        """Test that backoff delays increase exponentially."""
        import time

        logger = TalkSmithLogger(name="test")
        call_times = []

        @with_retry(max_attempts=3, initial_delay=0.1, backoff_factor=2.0, logger=logger)
        def operation():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise TransientError("Temporary failure")
            return "success"

        result = operation()
        assert result == "success"
        assert len(call_times) == 3

        # Check delays between attempts (with some tolerance)
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            assert 0.08 < delay1 < 0.15  # ~0.1s with tolerance

        if len(call_times) >= 3:
            delay2 = call_times[2] - call_times[1]
            assert 0.18 < delay2 < 0.25  # ~0.2s with tolerance

    def test_transient_error_exception(self):
        """Test TransientError exception type."""
        error = TransientError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"
