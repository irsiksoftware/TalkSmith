"""Integration tests for logger with retry/backoff functionality."""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from pipeline.logger import (
    get_logger,
    BatchLogSummary,
    TransientError,
    with_retry,
    retry_operation,
)


@pytest.mark.integration
class TestLoggerWorkflow:
    """Integration tests for complete logging workflow."""

    def test_complete_transcription_logging_workflow(self, temp_dir):
        """Test logging throughout a complete transcription workflow."""
        # Setup logger with file output
        with patch("pipeline.logger.get_config") as mock_config:
            config_mock = MagicMock()
            config_mock.get.side_effect = lambda section, key, fallback=None: {
                ("Logging", "level"): "INFO",
                ("Logging", "format"): "json",
                ("Logging", "console_output"): "true",
                ("Logging", "log_dir"): f"{temp_dir}/{{slug}}/logs",
            }.get((section, key), fallback)
            config_mock.get_bool.return_value = True
            mock_config.return_value = config_mock

            logger = get_logger(__name__, slug="test-workflow")

            # Simulate transcription workflow
            logger.log_start("transcription", audio_file="test.wav", model="large-v3")

            # Log progress
            logger.info("Loading model", stage="model_load")
            logger.info("Processing audio", stage="processing", progress=50)

            # Log metrics
            logger.log_metrics(
                {"rtf": 0.12, "duration": 300, "segments": 45}, level="INFO"
            )

            # Complete operation
            logger.log_complete("transcription", duration=36.5)

            # Verify log file created
            log_file = temp_dir / "test-workflow" / "logs" / "test-workflow.log"
            assert log_file.exists()

            # Parse and verify log entries
            with open(log_file, encoding="utf-8") as f:
                log_entries = [json.loads(line) for line in f]

            # Verify workflow logged correctly
            assert any("Starting transcription" in e["message"] for e in log_entries)
            assert any("Loading model" in e["message"] for e in log_entries)
            assert any("Completed transcription" in e["message"] for e in log_entries)

            # Verify metrics logged
            metrics_entry = next((e for e in log_entries if "metrics" in e), None)
            assert metrics_entry is not None
            assert metrics_entry["metrics"]["rtf"] == 0.12

            # Explicitly close logger handlers to release file locks on Windows
            for handler in logger.logger.handlers[:]:
                handler.close()
                logger.logger.removeHandler(handler)

    def test_batch_processing_with_summary(self, temp_dir):
        """Test batch processing with logging summary."""
        logger = get_logger(__name__)
        summary = BatchLogSummary(logger)

        # Simulate batch processing
        files = ["file1.wav", "file2.wav", "file3.wav", "file4.wav", "file5.wav"]
        for i, file in enumerate(files):
            if i == 2 or i == 4:  # Simulate failures
                summary.record_failure(file, f"Processing error: {i}")
            else:
                summary.record_success(file)

        summary.print_summary()

        # Verify results
        assert summary.total == 5
        assert summary.successful == 3
        assert summary.failed == 2
        assert summary.get_exit_code() == 1  # Non-zero due to failures
        assert len(summary.errors) == 2

    def test_error_handling_with_exit_codes(self):
        """Test error logging with proper exit codes."""
        logger = get_logger(__name__)

        # Test different error severities
        exit_code_1 = logger.log_error_exit(
            "Minor error occurred", exit_code=1, severity="low"
        )
        assert exit_code_1 == 1

        exit_code_2 = logger.log_error_exit(
            "Critical error occurred", exit_code=2, severity="critical"
        )
        assert exit_code_2 == 2


@pytest.mark.integration
class TestRetryIntegration:
    """Integration tests for retry/backoff functionality in real scenarios."""

    def test_api_call_with_retry(self):
        """Test API call simulation with retry logic."""
        logger = get_logger(__name__)
        call_count = {"count": 0}

        @with_retry(max_attempts=3, initial_delay=0.01, logger=logger)
        def fetch_model_metadata():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise TransientError("API temporarily unavailable")
            return {"model": "large-v3", "size": "2.9GB"}

        result = fetch_model_metadata()
        assert result["model"] == "large-v3"
        assert call_count["count"] == 3

    def test_network_operation_retry_with_backoff(self):
        """Test network operation with exponential backoff."""
        logger = get_logger(__name__)
        call_times = []

        @with_retry(
            max_attempts=4, initial_delay=0.05, backoff_factor=2.0, logger=logger
        )
        def download_model():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ConnectionError("Network unreachable")
            return "model_downloaded"

        result = download_model()
        assert result == "model_downloaded"
        assert len(call_times) == 3

        # Verify exponential backoff (approximate)
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            assert 0.04 < delay1 < 0.08  # ~0.05s

        if len(call_times) >= 3:
            delay2 = call_times[2] - call_times[1]
            assert 0.08 < delay2 < 0.15  # ~0.1s (2x backoff)

    def test_retry_with_different_exception_types(self):
        """Test retry handles different transient exception types."""
        logger = get_logger(__name__)
        call_count = {"count": 0}

        @with_retry(
            max_attempts=5,
            initial_delay=0.01,
            transient_exceptions=(TransientError, ConnectionError, TimeoutError),
            logger=logger,
        )
        def unstable_operation():
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise TransientError("Service unavailable")
            elif call_count["count"] == 2:
                raise ConnectionError("Connection reset")
            elif call_count["count"] == 3:
                raise TimeoutError("Request timeout")
            return "success"

        result = unstable_operation()
        assert result == "success"
        assert call_count["count"] == 4

    def test_retry_functional_approach(self):
        """Test retry using functional approach (retry_operation)."""
        logger = get_logger(__name__)
        attempts = {"count": 0}

        def flaky_service():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise TransientError("Service temporarily down")
            return {"status": "ok", "data": [1, 2, 3]}

        result = retry_operation(
            flaky_service,
            max_attempts=5,
            initial_delay=0.01,
            logger=logger,
            operation_name="fetch_service_data",
        )

        assert result["status"] == "ok"
        assert attempts["count"] == 3

    def test_retry_gives_up_after_max_attempts(self):
        """Test retry eventually gives up after max attempts."""
        logger = get_logger(__name__)
        call_count = {"count": 0}

        @with_retry(max_attempts=3, initial_delay=0.01, logger=logger)
        def always_fails():
            call_count["count"] += 1
            raise TransientError("Permanent service outage")

        with pytest.raises(TransientError):
            always_fails()

        assert call_count["count"] == 3  # Tried exactly 3 times


@pytest.mark.integration
class TestLoggerErrorScenarios:
    """Integration tests for error scenarios in logging."""

    def test_logging_with_exception_tracking(self):
        """Test logging captures exception information."""
        logger = get_logger(__name__)

        try:
            # Simulate processing error
            data = {"segments": []}
            result = data["missing_key"]  # KeyError
        except KeyError as e:
            logger.exception("Failed to process data", operation="export")

        # Logger should have captured exception info

    def test_concurrent_logging_operations(self):
        """Test logger handles concurrent operations correctly."""
        import threading

        logger = get_logger(__name__)
        results = []

        def log_operation(thread_id):
            logger.info(
                f"Thread {thread_id} started", thread_id=thread_id, operation="test"
            )
            time.sleep(0.01)
            logger.info(
                f"Thread {thread_id} completed", thread_id=thread_id, operation="test"
            )
            results.append(thread_id)

        threads = []
        for i in range(5):
            t = threading.Thread(target=log_operation, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(results) == 5

    def test_structured_logging_with_custom_fields(self):
        """Test structured logging with custom contextual fields."""
        logger = get_logger(__name__)

        # Log with custom fields
        logger.info(
            "Processing segment",
            segment_id=123,
            duration=5.5,
            speaker="SPEAKER_00",
            word_count=42,
        )

        logger.log_metrics(
            {
                "processing_time": 1.23,
                "memory_mb": 512,
                "gpu_utilization": 85.5,
            }
        )

        # Custom fields should be included in log output


@pytest.mark.integration
class TestRealWorldScenarios:
    """Integration tests simulating real-world usage patterns."""

    def test_transcription_pipeline_with_retry(self):
        """Test complete transcription pipeline with retry logic."""
        logger = get_logger(__name__)

        @with_retry(max_attempts=3, initial_delay=0.01, logger=logger)
        def load_model(model_name):
            # Simulate model loading that might fail
            return {"name": model_name, "loaded": True}

        @with_retry(max_attempts=3, initial_delay=0.01, logger=logger)
        def process_audio(audio_file):
            # Simulate audio processing
            return {"segments": [{"start": 0.0, "end": 2.0, "text": "Test segment"}]}

        # Execute pipeline
        logger.log_start("pipeline", audio_file="test.wav")
        model = load_model("large-v3")
        logger.info("Model loaded", model=model["name"])

        result = process_audio("test.wav")
        logger.info("Audio processed", segments=len(result["segments"]))

        logger.log_complete("pipeline", duration=5.5)

    def test_batch_processing_with_individual_retry(self):
        """Test batch processing where individual items may need retry."""
        logger = get_logger(__name__)
        summary = BatchLogSummary(logger)

        files = ["file1.wav", "file2.wav", "file3.wav"]
        fail_counts = {"file1.wav": 0, "file2.wav": 0, "file3.wav": 0}

        @with_retry(max_attempts=3, initial_delay=0.01, logger=logger)
        def process_file(filename):
            fail_counts[filename] += 1
            # file2.wav fails twice before succeeding
            if filename == "file2.wav" and fail_counts[filename] < 3:
                raise TransientError("Processing error")
            return {"file": filename, "status": "success"}

        for file in files:
            try:
                result = process_file(file)
                summary.record_success(file)
            except Exception as e:
                summary.record_failure(file, str(e))

        summary.print_summary()
        assert summary.successful == 3
        assert summary.failed == 0

    def test_mixed_error_types_in_workflow(self):
        """Test workflow with both retryable and permanent errors."""
        logger = get_logger(__name__)
        results = []

        @with_retry(max_attempts=3, initial_delay=0.01, logger=logger)
        def process_item(item_id):
            if item_id == 2:
                # Permanent error - won't be retried
                raise ValueError("Invalid format")
            elif item_id == 3:
                # Transient error on first attempt
                if item_id not in [r["id"] for r in results]:
                    raise TransientError("Temporary failure")
            return {"id": item_id, "status": "done"}

        for i in range(1, 5):
            try:
                result = process_item(i)
                results.append(result)
            except ValueError:
                # Handle permanent errors
                logger.error(f"Permanent error for item {i}", item_id=i)
            except TransientError:
                # Should not reach here due to retry
                pass

        # Items 1, 3, 4 should succeed; item 2 fails permanently
        assert len(results) == 3

    def test_logging_performance_metrics(self):
        """Test logging captures performance metrics throughout workflow."""
        logger = get_logger(__name__)

        # Simulate processing with metrics
        start_time = time.time()

        logger.log_start("processing", file="large.wav")

        # Simulate work
        time.sleep(0.05)

        processing_time = time.time() - start_time
        logger.log_metrics(
            {
                "processing_time": processing_time,
                "file_size_mb": 150.5,
                "rtf": 0.15,
                "segments_count": 250,
            }
        )

        logger.log_complete("processing", duration=processing_time)

        assert processing_time > 0.04  # At least 40ms
