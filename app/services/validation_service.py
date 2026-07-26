"""
Document Validation Service Module
====================================

Enforces security, MIME type, file size, and filename constraints on uploaded documents.

**Security Constraints:**
- Rejects executable files (.exe, .sh, .bat, etc.)
- Rejects double extensions (e.g. payload.pdf.exe)
- Rejects path traversal and hidden files (.env)
- Rejects empty files and files exceeding 100MB
"""

from __future__ import annotations

import mimetypes
import os
import re
from typing import ClassVar

from app.core.config import get_settings
from app.core.exceptions.base import BaseAppException


class DocumentValidationError(BaseAppException):
    """Raised when an uploaded document fails security or validation checks."""

    def __init__(self, detail: str) -> None:
        super().__init__(
            status_code=400,
            message=detail,
            error_code="DOCUMENT_VALIDATION_ERROR",
        )


class ValidationService:
    """Service handling file upload validation and sanitization."""

    EXECUTABLE_EXTENSIONS: ClassVar[set[str]] = {
        ".exe", ".sh", ".bat", ".cmd", ".vbs", ".dll", ".jar", ".msi",
        ".com", ".scr", ".pif", ".application", ".gadget", ".wsf", ".vbe",
        ".js", ".jse", ".ps1", ".ps2", ".psc1", ".psc2", ".py", ".rb",
    }

    # Standard magic bytes signatures for file headers
    MAGIC_SIGNATURES: ClassVar[dict[str, list[bytes]]] = {
        "application/pdf": [b"%PDF"],
        "image/png": [b"\x89PNG\r\n\x1a\n"],
        "image/jpeg": [b"\xff\xd8\xff"],
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [b"PK\x03\x04"],
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [b"PK\x03\x04"],
    }

    def __init__(self, settings: Any = None) -> None:
        self.settings = settings or get_settings()

    def validate_file(
        self,
        filename: str,
        content: bytes,
        declared_mime_type: str | None = None,
    ) -> tuple[str, str, int]:
        """
        Run complete validation pipeline on an uploaded file.

        Args:
            filename: Client-provided filename.
            content: Raw file byte content.
            declared_mime_type: MIME type sent by client in header.

        Returns:
            Tuple of (sanitized_filename, validated_mime_type, file_size).
        """
        # 1. Validate empty file
        file_size = len(content)
        if file_size == 0:
            raise DocumentValidationError("Empty files are not allowed")

        # 2. Validate max size
        if file_size > self.settings.max_upload_size_bytes:
            max_mb = self.settings.max_upload_size_bytes // (1024 * 1024)
            raise DocumentValidationError(f"File size exceeds maximum allowed limit of {max_mb}MB")

        # 3. Sanitize and validate filename
        clean_filename = self._sanitize_filename(filename)
        self._validate_filename_security(clean_filename)

        # 4. Extract and check extension
        ext = os.path.splitext(clean_filename)[1].lower()
        if not ext:
            raise DocumentValidationError("File has no extension")

        if ext not in self.settings.allowed_extensions:
            raise DocumentValidationError(
                f"File extension '{ext}' is not allowed. Allowed extensions: {self.settings.allowed_extensions}"
            )

        # 5. Validate MIME type
        detected_mime = self._detect_mime_type(content, clean_filename, declared_mime_type)
        if detected_mime not in self.settings.allowed_mime_types:
            raise DocumentValidationError(
                f"MIME type '{detected_mime}' is not allowed. Allowed types: {self.settings.allowed_mime_types}"
            )

        return clean_filename, detected_mime, file_size

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize client-provided filename to prevent directory traversal."""
        # Strip path components
        filename = os.path.basename(filename)
        # Remove control characters and null bytes
        filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)
        # Remove leading dot to prevent hidden files
        filename = filename.lstrip(".")
        if not filename:
            raise DocumentValidationError("Invalid or empty filename")
        return filename

    def _validate_filename_security(self, filename: str) -> None:
        """Enforce strict security checks on filename."""
        # Reject hidden files
        if filename.startswith("."):
            raise DocumentValidationError("Hidden files are not allowed")

        # Reject path traversal patterns
        if ".." in filename or "/" in filename or "\\" in filename:
            raise DocumentValidationError("Filename contains forbidden path characters")

        # Reject double extensions ending in executable extension (e.g. .pdf.exe)
        parts = filename.split(".")
        if len(parts) > 2:
            for part in parts[1:]:
                sub_ext = f".{part.lower()}"
                if sub_ext in self.EXECUTABLE_EXTENSIONS:
                    raise DocumentValidationError(f"Double extension with executable '{sub_ext}' is forbidden")

        # Reject pure executable extensions
        ext = os.path.splitext(filename)[1].lower()
        if ext in self.EXECUTABLE_EXTENSIONS:
            raise DocumentValidationError(f"Executable file extension '{ext}' is forbidden")

    def _detect_mime_type(
        self,
        content: bytes,
        filename: str,
        declared_mime: str | None = None,
    ) -> str:
        """Detect and verify MIME type using magic bytes header inspection."""
        ext = os.path.splitext(filename)[1].lower()

        # Check magic bytes for known types
        for mime, sigs in self.MAGIC_SIGNATURES.items():
            for sig in sigs:
                if content.startswith(sig):
                    return mime

        # Fallback to extension mimetypes lookup
        guess, _ = mimetypes.guess_type(filename)
        if guess and guess in self.settings.allowed_mime_types:
            return guess

        # Fallback to declared client MIME if valid
        if declared_mime and declared_mime in self.settings.allowed_mime_types:
            return declared_mime

        # Plain text fallback for .txt and .csv
        if ext == ".txt":
            return "text/plain"
        if ext == ".csv":
            return "text/csv"

        raise DocumentValidationError(f"Could not reliably determine valid MIME type for file '{filename}'")
