"""
Candidate Re-ranking & Snippet Highlighting Service Module
==========================================================

Domain service executing candidate re-ranking (Cross-Encoder / term overlap similarity)
and extracting highlighted text snippets.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles.
- Refines Top N candidate search matches into precision Top K results.
- Generates highlighted text snippets marking matched query terms.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class RerankingService:
    """
    Candidate Re-ranking & Highlight Service.

    Refines candidate search results using Cross-Encoder / term overlap similarity scoring
    and generates query-highlighted snippet previews.
    """

    def rerank_results(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Re-rank Top N candidates and return Top K results with highlighted text snippets.
        """
        if not candidates:
            return []

        query_terms = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 1]
        if not query_terms:
            return candidates[:top_k]

        reranked = []
        for cand in candidates:
            payload = cand.get("payload", {})
            text_snippet = payload.get("text_snippet", "")
            base_score = cand.get("score", 0.0)

            # Compute term overlap score bonus
            text_lower = text_snippet.lower()
            exact_match_count = sum(text_lower.count(term) for term in query_terms)
            phrase_bonus = 0.5 if query.lower() in text_lower else 0.0

            # Combined re-rank score
            overlap_score = min(1.0, (exact_match_count * 0.1) + phrase_bonus)
            final_score = round(0.7 * base_score + 0.3 * overlap_score, 4)

            # Generate highlighted snippet
            highlighted_text = self.highlight_terms(text_snippet, query_terms)

            reranked.append({
                "chunk_id": str(payload.get("chunk_id") or cand.get("id") or ""),
                "document_id": str(payload.get("document_id") or ""),
                "owner_id": str(payload.get("owner_id")) if payload.get("owner_id") is not None else None,
                "score": final_score,
                "page_number": payload.get("page_number") or 1,
                "chunk_index": payload.get("chunk_index") or 0,
                "snippet": text_snippet[:300] + ("..." if len(text_snippet) > 300 else ""),
                "highlighted_text": highlighted_text,
                "metadata": {
                    "original_filename": payload.get("original_filename", ""),
                    "mime_type": payload.get("mime_type", ""),
                    "visibility": payload.get("visibility", ""),
                    "language": payload.get("language", "en"),
                },
            })

        # Sort by re-ranked final_score descending
        reranked.sort(key=lambda x: x["score"], reverse=True)
        return reranked[:top_k]

    def highlight_terms(self, text: str, query_terms: list[str]) -> str:
        """Surround query term occurrences in text snippet with <mark> tags."""
        if not text or not query_terms:
            return text

        result = text
        pattern = re.compile(r"\b(" + "|".join(re.escape(t) for t in set(query_terms)) + r")\b", re.IGNORECASE)
        result = pattern.sub(r"<mark>\1</mark>", result)
        return result
