"""
Unit Tests for Language Detection Service Module
"""

from __future__ import annotations

import pytest

from app.services.language_detection_service import LanguageDetectionService


@pytest.mark.unit
def test_detect_language_english_text() -> None:
    service = LanguageDetectionService()
    text = "The quick brown fox jumps over the lazy dog. This is a financial document intelligence platform."
    lang = service.detect_language(text)
    assert lang == "en"


@pytest.mark.unit
def test_detect_language_fallback_on_short_text() -> None:
    service = LanguageDetectionService(fallback_language="en")
    lang = service.detect_language("hi")
    assert lang == "en"
