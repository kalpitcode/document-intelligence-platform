"""
Content Cleaning Service Module
=================================

Normalizes whitespace, standardizes Unicode (NFC), strips non-printable control characters,
preserves paragraph boundaries, and cleans OCR artifacts.
"""

from __future__ import annotations

import re
import unicodedata


class ContentCleaningService:
    """Service performing textual content normalization and cleaning."""

    # Regex matching control characters excluding \n (0x0A) and \t (0x09)
    CONTROL_CHARS_REGEX = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]")
    # Regex matching 3 or more consecutive newlines
    CONSECUTIVE_NEWLINES_REGEX = re.compile(r"\n{3,}")
    # Regex matching multiple horizontal spaces/tabs
    HORIZONTAL_WHITESPACE_REGEX = re.compile(r"[ \t\f\v]+")
    # Common OCR garbage patterns (isolated random non-alphanumeric noise symbols)
    OCR_NOISE_REGEX = re.compile(r"^[^\w\s]{4,}$")

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize raw extracted text.

        Args:
            text: Raw input text string.

        Returns:
            Normalized clean text string.
        """
        if not text:
            return ""

        # 1. Unicode normalization (NFC)
        normalized = unicodedata.normalize("NFC", text)

        # 2. Strip non-printable control characters
        cleaned = self.CONTROL_CHARS_REGEX.sub("", normalized)

        # 3. Clean line by line to normalize horizontal whitespace while preserving lines
        lines: list[str] = []
        for line in cleaned.splitlines():
            # Collapse internal horizontal whitespace
            stripped_line = self.HORIZONTAL_WHITESPACE_REGEX.sub(" ", line).strip()
            # Strip standalone OCR noise line if present
            if self.OCR_NOISE_REGEX.match(stripped_line):
                continue
            lines.append(stripped_line)

        rejoined = "\n".join(lines)

        # 4. Collapse 3+ consecutive newlines into double newlines (paragraph separation)
        final_text = self.CONSECUTIVE_NEWLINES_REGEX.sub("\n\n", rejoined)

        return final_text.strip()
