"""
Unit Tests for Document Validation Service
===========================================
"""

from __future__ import annotations

import pytest

from app.services.validation_service import DocumentValidationError, ValidationService


@pytest.fixture
def validator() -> ValidationService:
    return ValidationService()


def test_validate_valid_pdf(validator: ValidationService) -> None:
    content = b"%PDF-1.4 valid test pdf content"
    filename, mime, size = validator.validate_file("financial_report.pdf", content)

    assert filename == "financial_report.pdf"
    assert mime == "application/pdf"
    assert size == len(content)


def test_validate_empty_file_rejected(validator: ValidationService) -> None:
    with pytest.raises(DocumentValidationError, match="Empty files are not allowed"):
        validator.validate_file("empty.pdf", b"")


def test_validate_exceeds_max_size_rejected(validator: ValidationService) -> None:
    validator.settings.max_upload_size_bytes = 100  # Set low for test
    with pytest.raises(DocumentValidationError, match="exceeds maximum allowed limit"):
        validator.validate_file("large.pdf", b"%PDF" + b"x" * 200)


def test_validate_executable_rejected(validator: ValidationService) -> None:
    with pytest.raises(DocumentValidationError, match="is not allowed|forbidden"):
        validator.validate_file("malicious.exe", b"binary content")


def test_validate_double_extension_rejected(validator: ValidationService) -> None:
    with pytest.raises(DocumentValidationError, match="Double extension with executable"):
        validator.validate_file("payload.pdf.exe", b"%PDF-1.4 text")


def test_validate_hidden_file_rejected(validator: ValidationService) -> None:
    with pytest.raises(DocumentValidationError, match="no extension|not allowed"):
        validator.validate_file(".env", b"SECRET=123")


def test_validate_path_traversal_sanitized(validator: ValidationService) -> None:
    content = b"%PDF-1.4 text"
    filename, _, _ = validator.validate_file("../../etc/passwd.pdf", content)
    assert filename == "passwd.pdf"
