"""
Image Extraction Service Module
=================================

Extracts embedded images from PDF assets via PyMuPDF, uploads them to object storage
using StorageService, and returns extracted image metadata.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
import uuid

import fitz  # PyMuPDF
from PIL import Image
import structlog

from app.services.storage_service import StorageService

logger = structlog.get_logger(__name__)


@dataclass
class ExtractedImageData:
    """Dataclass storing extracted image metadata and stored key."""
    page_number: int
    storage_path: str
    width: int
    height: int
    format: str
    image_bytes: bytes


class ImageExtractionService:
    """Service extracting embedded images from documents and uploading to storage."""

    def __init__(self, storage_service: StorageService | None = None) -> None:
        self.storage_service = storage_service

    async def extract_images(
        self,
        document_id: uuid.UUID | str,
        content: bytes,
        mime_type: str = "application/pdf",
    ) -> list[ExtractedImageData]:
        """
        Extract embedded figures/photos from document binary content.

        Args:
            document_id: Parent document UUID.
            content: Raw document binary content.
            mime_type: Document MIME type.

        Returns:
            List of ExtractedImageData containing metadata and object storage path.
        """
        results: list[ExtractedImageData] = []
        if "pdf" not in mime_type.lower():
            return results

        doc_str_id = str(document_id)
        try:
            doc = fitz.open(stream=content, filetype="pdf")

            for page_idx in range(len(doc)):
                page_num = page_idx + 1
                page = doc[page_idx]
                image_list = page.get_images(full=True)

                for img_idx, img_info in enumerate(image_list):
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image.get("image")
                    img_ext = base_image.get("ext", "png").lower()

                    if not image_bytes:
                        continue

                    # Filter out tiny icon images (< 50x50)
                    try:
                        pil_img = Image.open(io.BytesIO(image_bytes))
                        width, height = pil_img.size
                        if width < 50 or height < 50:
                            continue
                    except Exception:
                        width, height = 0, 0

                    storage_key = f"extracted-images/{doc_str_id}/page_{page_num}_img_{img_idx+1}.{img_ext}"

                    if self.storage_service:
                        content_type = f"image/{img_ext if img_ext != 'jpg' else 'jpeg'}"
                        await self.storage_service.store_file(image_bytes, storage_key, content_type=content_type)

                    results.append(
                        ExtractedImageData(
                            page_number=page_num,
                            storage_path=storage_key,
                            width=width,
                            height=height,
                            format=img_ext,
                            image_bytes=image_bytes,
                        )
                    )
            doc.close()
        except Exception as exc:
            logger.warning("Error extracting embedded images from PDF", error=str(exc))

        return results
