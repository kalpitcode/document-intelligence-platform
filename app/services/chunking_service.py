"""
Chunking Service Module
========================

Creates deterministic, sequential text chunks with character offsets, page number mappings,
and token estimation for vector embedding ingestion.

**Architectural Rationale:**
- Target chunk size: 500 - 800 words.
- Overlap: 100 words.
- Calculates exact start_offset and end_offset in clean_text.
- Sequential chunk indices (0, 1, 2, ...).
"""

from __future__ import annotations

from dataclasses import dataclass
import uuid


@dataclass
class ChunkPayload:
    """Dataclass storing generated text chunk properties."""
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_number: int | None
    start_offset: int
    end_offset: int
    token_estimate: int


class ChunkingService:
    """Service producing deterministic, sequential text chunks."""

    def __init__(
        self,
        target_chunk_words: int = 600,
        overlap_words: int = 100,
        words_per_token_ratio: float = 0.75,
    ) -> None:
        self.target_chunk_words = target_chunk_words
        self.overlap_words = overlap_words
        self.words_per_token_ratio = words_per_token_ratio

    def create_chunks(
        self,
        document_id: uuid.UUID | str,
        clean_text: str,
        page_offsets: list[tuple[int, int]] | None = None,
    ) -> list[ChunkPayload]:
        """
        Split clean_text into deterministic, sequential overlapping chunks.

        Args:
            document_id: Target Document UUID.
            clean_text: Normalized document clean text.
            page_offsets: Optional list of (page_number, start_char_offset) tuples.

        Returns:
            List of ChunkPayload objects.
        """
        if isinstance(document_id, str):
            doc_uuid = uuid.UUID(document_id)
        else:
            doc_uuid = document_id

        if not clean_text or not clean_text.strip():
            return []

        words = clean_text.split()
        if not words:
            return []

        # Find word boundaries and character offsets in clean_text
        word_spans: list[tuple[str, int, int]] = []
        curr_pos = 0
        for w in words:
            w_start = clean_text.find(w, curr_pos)
            if w_start == -1:
                w_start = curr_pos
            w_end = w_start + len(w)
            word_spans.append((w, w_start, w_end))
            curr_pos = w_end

        total_words = len(word_spans)
        step = self.target_chunk_words - self.overlap_words
        if step <= 0:
            step = max(1, self.target_chunk_words // 2)

        chunks: list[ChunkPayload] = []
        chunk_idx = 0

        i = 0
        while i < total_words:
            end_i = min(i + self.target_chunk_words, total_words)
            chunk_word_spans = word_spans[i:end_i]

            chunk_text = clean_text[chunk_word_spans[0][1] : chunk_word_spans[-1][2]]
            start_offset = chunk_word_spans[0][1]
            end_offset = chunk_word_spans[-1][2]

            # Estimate page number based on start character offset if page_offsets provided
            page_num = self._resolve_page_number(start_offset, page_offsets)

            # Token estimate: approx 1.33 tokens per word (words / 0.75)
            token_estimate = max(1, int(len(chunk_word_spans) / self.words_per_token_ratio))

            chunks.append(
                ChunkPayload(
                    document_id=doc_uuid,
                    chunk_index=chunk_idx,
                    content=chunk_text,
                    page_number=page_num,
                    start_offset=start_offset,
                    end_offset=end_offset,
                    token_estimate=token_estimate,
                )
            )

            chunk_idx += 1
            if end_i >= total_words:
                break
            i += step

        return chunks

    def _resolve_page_number(
        self,
        offset: int,
        page_offsets: list[tuple[int, int]] | None,
    ) -> int | None:
        """Helper mapping character offset to page number."""
        if not page_offsets:
            return 1

        resolved_page = 1
        for page_num, start_char_idx in page_offsets:
            if offset >= start_char_idx:
                resolved_page = page_num
            else:
                break
        return resolved_page
