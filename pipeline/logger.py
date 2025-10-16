"""
Structured logging utility for TalkSmith.

Provides JSON-formatted logging with support for:
- Per-file log outputs to data/outputs/<slug>/logs/*.log
- Console and file output
- Contextual information (file, function, line number)
- Custom fields for metrics tracking
- Non-zero exit codes on errors
- Retry/backoff for transient errors
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Type
from logging.handlers import RotatingFileHandler
from functools import wraps

from config.settings import get_config


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON lines.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as a JSON string.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add custom fields from record.__dict__
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_data[key] = value

        return json.dumps(log_data)


class TalkSmithLogger:
    """
    Logger for TalkSmith with structured JSON output.
    """

    def __init__(
        self,
        name: str,
        slug: Optional[str] = None,
        console_output: bool = True,
        log_format: str = "json",
    ):
        """
        Initialize TalkSmith logger.

        Args:
            name: Logger name (typically __name__ of calling module)
            slug: Optional slug for file-specific logging (e.g., 'interview-2025-01-15')
            console_output: Whether to output to console
            log_format: 'json' or 'text' format for logs
        """
        self.logger = logging.getLogger(name)
        self.slug = slug
        self.log_format = log_format
        self.config = get_config()

        # Set log level from config
        level = self.config.get("Logging", "level", fallback="INFO")
        self.logger.setLevel(getattr(logging, level.upper()))

        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers(console_output)

    def _setup_handlers(self, console_output: bool):
        """
        Setup logging handlers for console and file output.

        Args:
            console_output: Whether to add console handler
        """
        # Choose formatter
        if self.log_format == "json":
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        # Console handler
        if console_output and self.config.get_bool(
            "Logging", "console_output", fallback=True
        ):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # File handler (if slug provided)
        if self.slug:
            # Get log directory and create it (this ensures it exists)
            log_dir = self._get_log_dir()
            log_file = log_dir / f"{self.slug}.log"

            file_handler = RotatingFileHandler(
                log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _get_log_dir(self) -> Path:
        """
        Get log directory path from config.

        Returns:
            Path to log directory
        """
        log_dir_template = self.config.get(
            "Logging", "log_dir", fallback="data/outputs/{slug}/logs"
        )

        log_dir_str = log_dir_template.replace("{slug}", self.slug or "default")
        log_dir = Path(log_dir_str)

        # Create if doesn't exist
        log_dir.mkdir(parents=True, exist_ok=True)

        return log_dir

    def debug(self, message: str, **kwargs):
        """Log debug message with optional custom fields."""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """Log info message with optional custom fields."""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with optional custom fields."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with optional custom fields."""
        self.logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message with optional custom fields."""
        self.logger.critical(message, extra=kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(message, extra=kwargs)

    def log_metrics(self, metrics: Dict[str, Any], level: str = "INFO"):
        """
        Log metrics data.

        Args:
            metrics: Dictionary of metrics to log
            level: Log level (default: INFO)
        """
        log_level = getattr(logging, level.upper())
        self.logger.log(log_level, "Metrics", extra={"metrics": metrics})

    def log_start(self, operation: str, **kwargs):
        """
        Log the start of an operation.

        Args:
            operation: Name of operation starting
            **kwargs: Additional context
        """
        self.info(f"Starting {operation}", operation=operation, stage="start", **kwargs)

    def log_complete(self, operation: str, duration: Optional[float] = None, **kwargs):
        """
        Log completion of an operation.

        Args:
            operation: Name of operation completed
            duration: Duration in seconds
            **kwargs: Additional context
        """
        extra = {"operation": operation, "stage": "complete"}
        if duration is not None:
            extra["duration_seconds"] = duration
        extra.update(kwargs)
        self.info(f"Completed {operation}", **extra)

    def log_error_exit(self, message: str, exit_code: int = 1, **kwargs):
        """
        Log error and return exit code.

        Args:
            message: Error message
            exit_code: Exit code to return (default: 1)
            **kwargs: Additional context

        Returns:
            Exit code for use in sys.exit()
        """
        self.error(message, exit_code=exit_code, **kwargs)
        return exit_code


def get_logger(
    name: str,
    slug: Optional[str] = None,
    console_output: bool = True,
    log_format: Optional[str] = None,
) -> TalkSmithLogger:
    """
    Get or create a TalkSmith logger instance.

    Args:
        name: Logger name
        slug: Optional slug for file-specific logging
        console_output: Whether to output to console
        log_format: 'json' or 'text' (defaults to config value)

    Returns:
        TalkSmithLogger instance
    """
    if log_format is None:
        config = get_config()
        log_format = config.get("Logging", "format", fallback="json")

    return TalkSmithLogger(
        name=name, slug=slug, console_output=console_output, log_format=log_format
    )


class BatchLogSummary:
    """
    Track and summarize results from batch operations.
    """

    def __init__(self, logger: TalkSmithLogger):
        """
        Initialize batch log summary.

        Args:
            logger: TalkSmith logger instance
        """
        self.logger = logger
        self.total = 0
        self.successful = 0
        self.failed = 0
        self.errors: list = []

    def record_success(self, item: str):
        """Record successful processing of an item."""
        self.total += 1
        self.successful += 1
        self.logger.debug(f"Success: {item}", item=item, status="success")

    def record_failure(self, item: str, error: str):
        """Record failed processing of an item."""
        self.total += 1
        self.failed += 1
        self.errors.append({"item": item, "error": error})
        self.logger.error(f"Failed: {item}", item=item, error=error, status="failed")

    def get_exit_code(self) -> int:
        """
        Get appropriate exit code based on results.

        Returns:
            0 if all succeeded, 1 if any failed
        """
        return 1 if self.failed > 0 else 0

    def print_summary(self):
        """Print summary of batch operation."""
        summary = {
            "total": self.total,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": (
                f"{(self.successful / self.total * 100):.1f}%"
                if self.total > 0
                else "N/A"
            ),
        }

        self.logger.info(
            f"Batch complete: {self.successful}/{self.total} successful", **summary
        )

        if self.errors:
            self.logger.error(f"Failed items: {len(self.errors)}", errors=self.errors)


class TransientError(Exception):
    """Exception for transient errors that should be retried."""

    pass


def with_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    transient_exceptions: Tuple[Type[Exception], ...] = (
        TransientError,
        ConnectionError,
        TimeoutError,
    ),
    logger: Optional[TalkSmithLogger] = None,
):
    """
    Decorator for retrying operations with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        backoff_factor: Multiplier for delay between retries (default: 2.0)
        initial_delay: Initial delay in seconds before first retry (default: 1.0)
        transient_exceptions: Tuple of exception types to retry on
        logger: Optional logger for logging retry attempts

    Returns:
        Decorated function with retry logic

    Example:
        @with_retry(max_attempts=3, logger=my_logger)
        def fetch_data():
            # Code that may fail transiently
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except transient_exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        if logger:
                            logger.error(
                                f"Failed after {max_attempts} attempts",
                                function=func.__name__,
                                attempts=attempt,
                                error=str(e),
                            )
                        raise

                    if logger:
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed, retrying in {delay}s",
                            function=func.__name__,
                            attempt=attempt,
                            delay=delay,
                            error=str(e),
                        )

                    time.sleep(delay)
                    delay *= backoff_factor

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def retry_operation(
    operation: Callable,
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    transient_exceptions: Tuple[Type[Exception], ...] = (
        TransientError,
        ConnectionError,
        TimeoutError,
    ),
    logger: Optional[TalkSmithLogger] = None,
    operation_name: Optional[str] = None,
) -> Any:
    """
    Retry an operation with exponential backoff (functional approach).

    Args:
        operation: Callable to execute
        max_attempts: Maximum number of retry attempts
        backoff_factor: Multiplier for delay between retries
        initial_delay: Initial delay in seconds before first retry
        transient_exceptions: Tuple of exception types to retry on
        logger: Optional logger for logging retry attempts
        operation_name: Name of operation for logging

    Returns:
        Result of the operation

    Raises:
        Exception: The last exception if all retries fail

    Example:
        result = retry_operation(
            lambda: fetch_data(),
            max_attempts=3,
            logger=my_logger
        )
    """
    delay = initial_delay
    last_exception = None
    op_name = operation_name or operation.__name__

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except transient_exceptions as e:
            last_exception = e

            if attempt == max_attempts:
                if logger:
                    logger.error(
                        f"Operation '{op_name}' failed after {max_attempts} attempts",
                        operation=op_name,
                        attempts=attempt,
                        error=str(e),
                    )
                raise

            if logger:
                msg = (
                    f"Operation '{op_name}' attempt {attempt}/"
                    f"{max_attempts} failed, retrying in {delay}s"
                )
                logger.warning(
                    msg,
                    operation=op_name,
                    attempt=attempt,
                    delay=delay,
                    error=str(e),
                )

            time.sleep(delay)
            delay *= backoff_factor

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception


if __name__ == "__main__":
    # Example usage
    logger = get_logger(__name__, slug="example-2025-01-15")

    logger.info("Starting transcription", audio_file="test.wav")
    logger.log_metrics({"rtf": 0.12, "duration": 3600, "model": "large-v3"})
    logger.log_complete("transcription", duration=432.5)

    # Batch example
    batch = BatchLogSummary(logger)
    batch.record_success("file1.wav")
    batch.record_success("file2.wav")
    batch.record_failure("file3.wav", "File not found")
    batch.print_summary()

    exit_code = batch.get_exit_code()
    print(f"Exit code: {exit_code}")

    # Retry example
    @with_retry(max_attempts=3, logger=logger)
    def fetch_api_data():
        # Simulate transient failure
        import random

        if random.random() < 0.7:
            raise TransientError("API temporarily unavailable")
        return {"status": "success"}

    try:
        result = fetch_api_data()
        print(f"API call result: {result}")
    except TransientError:
        print("API call failed after all retries")
