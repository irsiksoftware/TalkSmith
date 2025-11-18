"""Unit tests for PII redaction module."""

import json
import tempfile
from pathlib import Path

import pytest

from pipeline.redact_pii import PIIRedactor, create_whitelist_template


class TestPIIRedactor:
    """Tests for PIIRedactor class."""

    @pytest.fixture
    def redactor(self):
        """Create a basic PIIRedactor instance."""
        return PIIRedactor()

    @pytest.fixture
    def redactor_with_whitelist(self, tmp_path):
        """Create PIIRedactor with a whitelist."""
        whitelist_path = tmp_path / "whitelist.txt"
        whitelist_path.write_text("support@example.com\n555-0100\n192.168.1.1\n")
        return PIIRedactor(str(whitelist_path))

    def test_redact_email_basic(self, redactor):
        """Test basic email redaction."""
        text = "Contact me at john.doe@example.com for details."
        result = redactor.redact_emails(text)
        assert "[EMAIL_REDACTED]" in result
        assert "john.doe@example.com" not in result

    def test_redact_multiple_emails(self, redactor):
        """Test redacting multiple emails."""
        text = "Email alice@test.com or bob@company.org"
        result = redactor.redact_emails(text)
        assert result.count("[EMAIL_REDACTED]") == 2
        assert "alice@test.com" not in result
        assert "bob@company.org" not in result

    def test_redact_email_with_plus(self, redactor):
        """Test email with plus addressing."""
        text = "Send to user+tag@example.com"
        result = redactor.redact_emails(text)
        assert "[EMAIL_REDACTED]" in result
        assert "user+tag@example.com" not in result

    def test_redact_phone_basic(self, redactor):
        """Test basic phone number redaction."""
        text = "Call me at 555-123-4567"
        result = redactor.redact_phones(text)
        assert "[PHONE_REDACTED]" in result
        assert "555-123-4567" not in result

    def test_redact_phone_various_formats(self, redactor):
        """Test phone number redaction with various formats."""
        texts = [
            "Call 5551234567",
            "Phone: (555) 123-4567",
            "Dial +1-555-123-4567",
            "Contact: 555.123.4567",
        ]
        for text in texts:
            result = redactor.redact_phones(text)
            assert "[PHONE_REDACTED]" in result

    def test_redact_ssn(self, redactor):
        """Test SSN redaction."""
        text = "My SSN is 123-45-6789"
        result = redactor.redact_ssn(text)
        assert "[SSN_REDACTED]" in result
        assert "123-45-6789" not in result

    def test_redact_ssn_no_dashes(self, redactor):
        """Test SSN redaction without dashes."""
        text = "SSN: 123456789"
        result = redactor.redact_ssn(text)
        assert "[SSN_REDACTED]" in result

    def test_redact_credit_card(self, redactor):
        """Test credit card redaction."""
        text = "Card: 4532-1234-5678-9010"
        result = redactor.redact_credit_cards(text)
        assert "[CREDIT_CARD_REDACTED]" in result
        assert "4532-1234-5678-9010" not in result

    def test_redact_credit_card_no_dashes(self, redactor):
        """Test credit card without dashes."""
        text = "Card number 4532123456789010"
        result = redactor.redact_credit_cards(text)
        assert "[CREDIT_CARD_REDACTED]" in result

    def test_redact_ip_address(self, redactor):
        """Test IP address redaction."""
        text = "Server at 192.168.1.100"
        result = redactor.redact_ip_addresses(text)
        assert "[IP_REDACTED]" in result
        assert "192.168.1.100" not in result

    def test_preserve_version_numbers(self, redactor):
        """Test that version numbers are not redacted."""
        text = "Version 1.0.0.0 released"
        result = redactor.redact_ip_addresses(text)
        assert "1.0.0.0" in result
        assert "[IP_REDACTED]" not in result

    def test_whitelist_email(self, redactor_with_whitelist):
        """Test whitelisted email is not redacted."""
        text = "Contact support@example.com"
        result = redactor_with_whitelist.redact_emails(text)
        assert "support@example.com" in result
        assert "[EMAIL_REDACTED]" not in result

    def test_whitelist_phone(self, redactor_with_whitelist):
        """Test whitelisted phone is not redacted."""
        text = "Call 555-0100 for help"
        result = redactor_with_whitelist.redact_phones(text)
        assert "555-0100" in result
        assert "[PHONE_REDACTED]" not in result

    def test_whitelist_ip(self, redactor_with_whitelist):
        """Test whitelisted IP is not redacted."""
        text = "Connect to 192.168.1.1"
        result = redactor_with_whitelist.redact_ip_addresses(text)
        assert "192.168.1.1" in result
        assert "[IP_REDACTED]" not in result

    def test_whitelist_case_insensitive(self, tmp_path):
        """Test whitelist is case-insensitive."""
        whitelist_path = tmp_path / "whitelist.txt"
        whitelist_path.write_text("SUPPORT@EXAMPLE.COM\n")
        redactor = PIIRedactor(str(whitelist_path))

        text = "Contact support@example.com"
        result = redactor.redact_emails(text)
        assert "support@example.com" in result

    def test_redact_all(self, redactor):
        """Test redacting all PII types at once."""
        text = (
            "Email john@example.com, "
            "call 555-123-4567, "
            "SSN 123-45-6789, "
            "card 4532123456789010"
        )
        result = redactor.redact_all(text)
        assert "[EMAIL_REDACTED]" in result
        assert "[PHONE_REDACTED]" in result
        assert "[SSN_REDACTED]" in result
        assert "[CREDIT_CARD_REDACTED]" in result

    def test_no_pii_unchanged(self, redactor):
        """Test that text without PII is unchanged."""
        text = "This is a normal sentence without any PII."
        result = redactor.redact_all(text)
        assert result == text

    def test_redact_segments_text(self, redactor):
        """Test redacting PII from segment text."""
        segments = [
            {"start": 0.0, "end": 2.0, "text": "My email is john@example.com"},
            {"start": 2.0, "end": 4.0, "text": "Call me at 555-123-4567"},
        ]
        result = redactor.redact_segments(segments)
        assert "[EMAIL_REDACTED]" in result[0]["text"]
        assert "[PHONE_REDACTED]" in result[1]["text"]

    def test_redact_segments_words(self, redactor):
        """Test redacting PII from word-level text."""
        segments = [
            {
                "start": 0.0,
                "end": 2.0,
                "text": "Email john@example.com",
                "words": [
                    {"start": 0.0, "end": 0.5, "word": "Email"},
                    {"start": 0.5, "end": 1.5, "word": "john@example.com"},
                ],
            }
        ]
        result = redactor.redact_segments(segments, redact_words=True)
        assert "[EMAIL_REDACTED]" in result[0]["words"][1]["word"]

    def test_redact_segments_preserves_structure(self, redactor):
        """Test that redaction preserves segment structure."""
        segments = [{"start": 0.0, "end": 2.0, "text": "Hello there", "speaker": "SPEAKER_01"}]
        result = redactor.redact_segments(segments)
        assert result[0]["start"] == 0.0
        assert result[0]["end"] == 2.0
        assert result[0]["speaker"] == "SPEAKER_01"

    def test_redact_segments_skip_text(self, redactor):
        """Test skipping text redaction."""
        segments = [{"start": 0.0, "end": 2.0, "text": "My email is john@example.com"}]
        result = redactor.redact_segments(segments, redact_text=False)
        assert "john@example.com" in result[0]["text"]

    def test_redact_segments_skip_words(self, redactor):
        """Test skipping word redaction."""
        segments = [
            {
                "start": 0.0,
                "end": 2.0,
                "text": "Email john@example.com",
                "words": [{"start": 0.5, "end": 1.5, "word": "john@example.com"}],
            }
        ]
        result = redactor.redact_segments(segments, redact_words=False)
        assert "john@example.com" in result[0]["words"][0]["word"]

    def test_redact_transcript_file(self, redactor, tmp_path):
        """Test redacting a transcript file."""
        input_path = tmp_path / "transcript.txt"
        input_path.write_text("Contact john@example.com or call 555-123-4567")

        output_path = redactor.redact_transcript_file(str(input_path))
        output_file = Path(output_path)

        assert output_file.exists()
        content = output_file.read_text()
        assert "[EMAIL_REDACTED]" in content
        assert "[PHONE_REDACTED]" in content
        assert "john@example.com" not in content

    def test_redact_transcript_file_custom_output(self, redactor, tmp_path):
        """Test redacting with custom output path."""
        input_path = tmp_path / "input.txt"
        output_path = tmp_path / "output" / "redacted.txt"
        input_path.write_text("Email: test@example.com")

        result_path = redactor.redact_transcript_file(str(input_path), str(output_path))

        assert Path(result_path).exists()
        assert Path(result_path) == output_path

    def test_redact_transcript_file_creates_dirs(self, redactor, tmp_path):
        """Test that output directory is created if needed."""
        input_path = tmp_path / "input.txt"
        output_path = tmp_path / "new_dir" / "redacted.txt"
        input_path.write_text("Test content")

        redactor.redact_transcript_file(str(input_path), str(output_path))

        assert output_path.exists()

    def test_load_whitelist_nonexistent_file(self):
        """Test loading nonexistent whitelist file."""
        redactor = PIIRedactor("/nonexistent/path/whitelist.txt")
        assert len(redactor.whitelist) == 0

    def test_empty_whitelist(self, tmp_path):
        """Test empty whitelist file."""
        whitelist_path = tmp_path / "empty.txt"
        whitelist_path.write_text("")
        redactor = PIIRedactor(str(whitelist_path))
        assert len(redactor.whitelist) == 0


class TestCreateWhitelistTemplate:
    """Tests for create_whitelist_template function."""

    def test_create_whitelist_template(self, tmp_path):
        """Test creating whitelist template."""
        output_path = tmp_path / "whitelist.txt"
        create_whitelist_template(str(output_path))

        assert output_path.exists()
        content = output_path.read_text()
        assert "PII Redaction Whitelist" in content
        assert "support@example.com" in content

    def test_create_whitelist_template_creates_dirs(self, tmp_path):
        """Test that template creation creates parent directories."""
        output_path = tmp_path / "new_dir" / "whitelist.txt"
        create_whitelist_template(str(output_path))

        assert output_path.exists()


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    @pytest.fixture
    def redactor(self):
        """Create a basic PIIRedactor instance."""
        return PIIRedactor()

    def test_empty_text(self, redactor):
        """Test redacting empty text."""
        result = redactor.redact_all("")
        assert result == ""

    def test_unicode_text(self, redactor):
        """Test redacting text with unicode characters."""
        text = "Email: test@例え.com and 日本語 text"
        result = redactor.redact_all(text)
        assert "日本語" in result

    def test_adjacent_pii(self, redactor):
        """Test adjacent PII items."""
        text = "john@example.com555-123-4567"
        result = redactor.redact_all(text)
        assert "[EMAIL_REDACTED]" in result
        assert "[PHONE_REDACTED]" in result

    def test_pii_at_boundaries(self, redactor):
        """Test PII at text boundaries."""
        text = "test@example.com"
        result = redactor.redact_emails(text)
        assert result == "[EMAIL_REDACTED]"

    def test_partial_patterns_not_redacted(self, redactor):
        """Test that partial patterns are not redacted."""
        text = "The number 123 is not a phone number"
        result = redactor.redact_phones(text)
        assert "123" in result
        assert "[PHONE_REDACTED]" not in result

    def test_redact_segments_empty_list(self, redactor):
        """Test redacting empty segment list."""
        result = redactor.redact_segments([])
        assert result == []

    def test_redact_segments_missing_fields(self, redactor):
        """Test redacting segments with missing fields."""
        segments = [{"start": 0.0, "end": 1.0}]
        result = redactor.redact_segments(segments)
        assert len(result) == 1
        assert "text" not in result[0]

    def test_multiple_whitespaces(self, redactor):
        """Test PII with multiple whitespaces."""
        text = "Call   555-123-4567   now"
        result = redactor.redact_phones(text)
        assert "[PHONE_REDACTED]" in result
