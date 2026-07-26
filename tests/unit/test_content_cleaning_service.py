"""
Unit Tests for Content Cleaning Service Module
"""

from __future__ import annotations

import pytest

from app.services.content_cleaning_service import ContentCleaningService


@pytest.mark.unit
def test_clean_text_normalizes_whitespace_and_newlines() -> None:
    service = ContentCleaningService()
    raw = "  Header   Text  \n\n\n\nParagraph   1  with   extra   spaces.\n\n\nParagraph 2.  "
    cleaned = service.clean_text(raw)

    assert "Header Text" in cleaned
    assert "Paragraph 1 with extra spaces." in cleaned
    assert "Paragraph 2." in cleaned
    assert "\n\n\n" not in cleaned


@pytest.mark.unit
def test_clean_text_strips_control_characters() -> None:
    service = ContentCleaningService()
    raw = "Hello\x00 World\x07!\n\nParagraph 2."
    cleaned = service.clean_text(raw)

    assert cleaned == "Hello World!\n\nParagraph 2."


@pytest.mark.unit
def test_clean_text_empty_string() -> None:
    service = ContentCleaningService()
    assert service.clean_text("") == ""
