"""
OCR Service Module
===================

Optical Character Recognition service utilizing pytesseract and Pillow for extracting text
and confidence metrics from scanned PDFs and image files.

**Architectural Rationale:**
- Support Scanned PDFs, Image-based PDFs, PNG, JPEG.
- Calculates mean OCR confidence score across recognized text data.
- Implements safe fallback handling when Tesseract binary is not installed on system.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

from PIL import Image
import structlog

logger = structlog.get_logger(__name__)

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    pytesseract = None  # type: ignore[assignment]


@dataclass
class OCRResult:
    """Dataclass holding OCR extraction text and confidence score."""
    text: str
    confidence: float
    page_number: int = 1


class OCRService:
    """Service wrapping Tesseract OCR engine for image and scanned page text extraction."""

    def __init__(self, tesseract_cmd: str | None = None) -> None:
        if PYTESSERACT_AVAILABLE and tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def extract_text_from_image(
        self,
        image_bytes: bytes,
        page_number: int = 1,
        lang: str = "eng",
    ) -> OCRResult:
        """
        Extract text and calculate confidence score from raw image bytes.

        Args:
            image_bytes: Binary image payload (PNG, JPEG, TIFF, BMP).
            page_number: 1-based page index.
            lang: Tesseract language model code (default 'eng').

        Returns:
            OCRResult containing extracted text and average confidence score (0.0 to 100.0).
        """
        if not PYTESSERACT_AVAILABLE:
            logger.warning("pytesseract library not available; returning empty OCR result")
            return OCRResult(text="", confidence=0.0, page_number=page_number)

        try:
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")

            # Extract detailed dictionary containing confidence scores per word
            data: dict[str, list[Any]] = pytesseract.image_to_data(
                image,
                lang=lang,
                output_type=pytesseract.Output.DICT,
            )

            texts: list[str] = []
            confidences: list[float] = []

            for text, conf in zip(data.get("text", []), data.get("conf", []), strict=False):
                clean_w = str(text).strip()
                try:
                    conf_val = float(conf)
                except (ValueError, TypeError):
                    conf_val = -1.0

                if clean_w:
                    texts.append(clean_w)
                    if conf_val >= 0:
                        confidences.append(conf_val)

            full_text = " ".join(texts)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

            return OCRResult(
                text=full_text,
                confidence=round(avg_conf, 2),
                page_number=page_number,
            )

        except Exception as exc:
            # Handle TesseractNotFoundError or OS runtime error gracefully
            logger.warning(
                "OCR processing error (Tesseract binary missing or image corrupt)",
                error=str(exc),
                page_number=page_number,
            )
            return OCRResult(
                text="",
                confidence=0.0,
                page_number=page_number,
            )

    def extract_text_from_pil_image(
        self,
        image: Image.Image,
        page_number: int = 1,
        lang: str = "eng",
    ) -> OCRResult:
        """Perform OCR directly on a PIL Image instance."""
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return self.extract_text_from_image(buffer.getvalue(), page_number=page_number, lang=lang)
