"""
Unit Tests for OCR Service Module
"""

from __future__ import annotations

import io
from PIL import Image
import pytest

from app.services.ocr_service import OCRResult, OCRService


@pytest.mark.unit
def test_ocr_service_initialization() -> None:
    service = OCRService()
    assert service is not None


@pytest.mark.unit
def test_ocr_extract_text_from_synthetic_image() -> None:
    # Create simple RGB image in memory
    img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()

    service = OCRService()
    result = service.extract_text_from_image(img_bytes, page_number=1)

    assert isinstance(result, OCRResult)
    assert result.page_number == 1
    assert isinstance(result.confidence, float)
    assert isinstance(result.text, str)
