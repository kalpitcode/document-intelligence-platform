"""
Table Extraction Service Module
=================================

Extracts tabular structure from PDF documents using pdfplumber, preserving row and column layout
into clean, structured JSON payloads.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

import pdfplumber
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TableData:
    """Dataclass holding extracted table payload and page context."""
    page_number: int
    table_index: int
    rows: list[list[str]]
    headers: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize table data into structured JSON dictionary."""
        return {
            "page_number": self.page_number,
            "table_index": self.table_index,
            "headers": self.headers or [],
            "rows": self.rows,
            "row_count": len(self.rows),
            "column_count": len(self.headers) if self.headers else (len(self.rows[0]) if self.rows else 0),
        }


class TableExtractionService:
    """Service extracting tabular content from PDF documents."""

    def extract_tables(self, content: bytes, mime_type: str = "application/pdf") -> list[TableData]:
        """
        Extract tables from PDF document content.

        Args:
            content: PDF binary content.
            mime_type: File MIME type.

        Returns:
            List of TableData objects representing extracted tables.
        """
        tables: list[TableData] = []
        if "pdf" not in mime_type.lower():
            return tables

        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    page_num = page_idx + 1
                    extracted_raw_tables = page.extract_tables()

                    for t_idx, raw_table in enumerate(extracted_raw_tables):
                        if not raw_table or not any(raw_table):
                            continue

                        # Clean null/None values into strings
                        cleaned_rows: list[list[str]] = [
                            [str(cell or "").strip() for cell in row]
                            for row in raw_table
                            if any(cell is not None and str(cell).strip() for cell in row)
                        ]

                        if not cleaned_rows:
                            continue

                        # Treat first non-empty row as header if valid
                        headers = cleaned_rows[0] if len(cleaned_rows) > 1 else None
                        body_rows = cleaned_rows[1:] if len(cleaned_rows) > 1 else cleaned_rows

                        tables.append(
                            TableData(
                                page_number=page_num,
                                table_index=t_idx,
                                rows=body_rows,
                                headers=headers,
                            )
                        )
        except Exception as exc:
            logger.warning("Error extracting tables from PDF via pdfplumber", error=str(exc))

        return tables
