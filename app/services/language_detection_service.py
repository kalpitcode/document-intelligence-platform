"""
Language Detection Service Module
==================================

Detects primary language of text using langdetect with default ISO code fallback ('en').
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)

try:
    from langdetect import DetectorFactory, detect
    # Enforce deterministic language detection results
    DetectorFactory.seed = 0
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    detect = None  # type: ignore[assignment]


class LanguageDetectionService:
    """Service identifying primary language of text payloads."""

    def __init__(self, fallback_language: str = "en") -> None:
        self.fallback_language = fallback_language

    def detect_language(self, text: str) -> str:
        """
        Detect ISO 639-1 language code of input text.

        Args:
            text: Normalized document clean text.

        Returns:
            ISO 639-1 language string (e.g. 'en', 'es', 'de').
        """
        if not text or len(text.strip()) < 10 or not LANGDETECT_AVAILABLE:
            return self.fallback_language

        try:
            # Use top sample snippet (up to 2000 chars) for speed & accuracy
            sample = text.strip()[:2000]
            detected_lang = detect(sample)
            return str(detected_lang).lower()
        except Exception as exc:
            logger.debug("Language detection failed; defaulting to fallback", error=str(exc))
            return self.fallback_language
