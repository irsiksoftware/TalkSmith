"""
PII (Personally Identifiable Information) redaction module.

Provides simple redaction pass for common PII patterns with whitelist support.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set


class PIIRedactor:
    """Redacts common PII patterns from text."""

    # Common PII patterns
    EMAIL_PATTERN = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}"
    # Matches various phone formats: 555-123-4567, (555) 123-4567, +1-555-123-4567, 5551234567
    PHONE_PATTERN = r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    SSN_PATTERN = r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"
    CREDIT_CARD_PATTERN = r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
    IP_ADDRESS_PATTERN = r"(?:\d{1,3}\.){3}\d{1,3}"

    def __init__(self, whitelist_path: Optional[str] = None):
        """
        Initialize the PII redactor.

        Args:
            whitelist_path: Path to file containing whitelisted terms (one per line)
        """
        self.whitelist: Set[str] = set()
        if whitelist_path:
            self.load_whitelist(whitelist_path)

    def load_whitelist(self, path: str) -> None:
        """
        Load whitelist from file.

        Args:
            path: Path to whitelist file
        """
        whitelist_file = Path(path)
        if whitelist_file.exists():
            with open(whitelist_file, "r", encoding="utf-8") as f:
                self.whitelist = {line.strip() for line in f if line.strip()}

    def is_whitelisted(self, text: str) -> bool:
        """
        Check if text is in whitelist.

        Args:
            text: Text to check

        Returns:
            True if whitelisted, False otherwise
        """
        return text.lower() in {item.lower() for item in self.whitelist}

    def redact_emails(self, text: str) -> str:
        """
        Redact email addresses.

        Args:
            text: Input text

        Returns:
            Text with emails redacted
        """

        def replace_email(match):
            email = match.group(0)
            if self.is_whitelisted(email):
                return email
            return "[EMAIL_REDACTED]"

        return re.sub(self.EMAIL_PATTERN, replace_email, text)

    def redact_phones(self, text: str) -> str:
        """
        Redact phone numbers.

        Args:
            text: Input text

        Returns:
            Text with phone numbers redacted
        """

        def replace_phone(match):
            phone = match.group(0)
            if self.is_whitelisted(phone):
                return phone
            return "[PHONE_REDACTED]"

        return re.sub(self.PHONE_PATTERN, replace_phone, text)

    def redact_ssn(self, text: str) -> str:
        """
        Redact Social Security Numbers.

        Args:
            text: Input text

        Returns:
            Text with SSNs redacted
        """

        def replace_ssn(match):
            ssn = match.group(0)
            if self.is_whitelisted(ssn):
                return ssn
            return "[SSN_REDACTED]"

        return re.sub(self.SSN_PATTERN, replace_ssn, text)

    def redact_credit_cards(self, text: str) -> str:
        """
        Redact credit card numbers.

        Args:
            text: Input text

        Returns:
            Text with credit card numbers redacted
        """

        def replace_cc(match):
            cc = match.group(0)
            if self.is_whitelisted(cc):
                return cc
            return "[CREDIT_CARD_REDACTED]"

        return re.sub(self.CREDIT_CARD_PATTERN, replace_cc, text)

    def redact_ip_addresses(self, text: str) -> str:
        """
        Redact IP addresses.

        Args:
            text: Input text

        Returns:
            Text with IP addresses redacted
        """

        def replace_ip(match):
            ip = match.group(0)
            if self.is_whitelisted(ip):
                return ip
            # Don't redact version numbers or dates like "1.0.0.0"
            if re.match(r"^[0-2]\.[0-9]\.[0-9]", ip):
                return ip
            return "[IP_REDACTED]"

        return re.sub(self.IP_ADDRESS_PATTERN, replace_ip, text)

    def redact_all(self, text: str) -> str:
        """
        Apply all redaction patterns.

        Args:
            text: Input text

        Returns:
            Text with all PII redacted
        """
        # Process credit cards before phones to avoid conflicts
        text = self.redact_credit_cards(text)
        text = self.redact_ssn(text)
        text = self.redact_emails(text)
        text = self.redact_phones(text)
        text = self.redact_ip_addresses(text)
        return text

    def redact_segments(
        self, segments: List[Dict], redact_text: bool = True, redact_words: bool = True
    ) -> List[Dict]:
        """
        Redact PII from transcript segments.

        Args:
            segments: List of segment dictionaries
            redact_text: Whether to redact segment text
            redact_words: Whether to redact word-level text

        Returns:
            Segments with PII redacted
        """
        redacted_segments = []

        for segment in segments:
            redacted_segment = segment.copy()

            # Redact segment text
            if redact_text and "text" in redacted_segment:
                redacted_segment["text"] = self.redact_all(redacted_segment["text"])

            # Redact word-level text
            if redact_words and "words" in redacted_segment:
                redacted_words = []
                for word in redacted_segment["words"]:
                    redacted_word = word.copy()
                    if "word" in redacted_word:
                        redacted_word["word"] = self.redact_all(redacted_word["word"])
                    redacted_words.append(redacted_word)
                redacted_segment["words"] = redacted_words

            redacted_segments.append(redacted_segment)

        return redacted_segments

    def redact_transcript_file(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        Redact PII from a text transcript file.

        Args:
            input_path: Path to input transcript file
            output_path: Path to output file (default: input_path with _redacted suffix)

        Returns:
            Path to output file
        """
        input_file = Path(input_path)

        # Read input
        with open(input_file, "r", encoding="utf-8") as f:
            text = f.read()

        # Redact
        redacted_text = self.redact_all(text)

        # Determine output path
        if output_path is None:
            output_path = input_file.parent / f"{input_file.stem}_redacted{input_file.suffix}"
        else:
            output_path = Path(output_path)

        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(redacted_text)

        return str(output_path)


def create_whitelist_template(output_path: str = "whitelist.txt") -> None:
    """
    Create a whitelist template file.

    Args:
        output_path: Path to create whitelist file
    """
    template = """# PII Redaction Whitelist
# One entry per line. Case-insensitive.
# Add emails, phone numbers, or other patterns that should NOT be redacted.

# Example entries:
# support@example.com
# 555-0100
# 192.168.1.1
"""

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(template)
