"""
Hybrid Search Domain Service Module
====================================

Fuses Dense Vector Semantic Search (Qdrant) and BM25 Sparse Keyword Search (`rank-bm25`),
normalizes match scores, applies Reciprocal Rank Fusion (RRF), and enforces security & metadata filters.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles.
- Combines deep semantic retrieval with exact keyword term matching.
- Implements Reciprocal Rank Fusion (RRF) algorithm to produce optimal rank fusion results.
- Strict security filtering respecting ownership, public visibility, and RBAC rules.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Sequence

from app.models.user import UserModel
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)

# Try rank_bm25 import
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25Okapi = None
    BM25_AVAILABLE = False


def _tokenize(text: str) -> list[str]:
    """Tokenize query or document text into lowercase terms."""
    import re
    return [w.lower() for w in re.findall(r"\w+", text) if len(w) > 1]


class HybridSearchService:
    """
    Hybrid Search Orchestrator.

    Executes vector semantic search, BM25 keyword search, RRF score fusion,
    and metadata security filtering.
    """

    def __init__(
        self,
        vector_service: VectorService,
        embedding_service: EmbeddingService,
    ) -> None:
        self.vector_service = vector_service
        self.embedding_service = embedding_service

    async def execute_search(
        self,
        query: str,
        current_user: UserModel,
        query_type: str = "hybrid",
        top_k: int = 10,
        score_threshold: float | None = None,
        filters: dict[str, Any] | None = None,
        all_chunks: Sequence[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute Hybrid / Semantic / Keyword Search with security filtering.

        Returns list of candidate match dicts containing payload and combined match score.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        search_filters = self._build_security_filters(current_user, filters)

        semantic_results: list[dict[str, Any]] = []
        keyword_results: list[dict[str, Any]] = []

        # 1. Semantic Search
        if query_type in ("semantic", "hybrid"):
            query_vector = await self.embedding_service.generate_embedding(clean_query)
            semantic_results = await self.vector_service.search_similar_chunks(
                query_vector=query_vector,
                limit=top_k * 2,
                filters=search_filters,
                score_threshold=score_threshold,
            )

        # 2. Keyword Search
        if query_type in ("keyword", "hybrid") and all_chunks:
            keyword_results = self._execute_bm25_search(
                query=clean_query,
                all_chunks=all_chunks,
                limit=top_k * 2,
                current_user=current_user,
                filters=filters,
            )

        # 3. Combine & Rank Fusion
        if query_type == "semantic":
            fused = semantic_results
        elif query_type == "keyword":
            fused = keyword_results
        else:
            fused = self._reciprocal_rank_fusion(semantic_results, keyword_results, rrf_k=60)

        # Apply score threshold if specified
        if score_threshold is not None:
            fused = [r for r in fused if r.get("score", 0.0) >= score_threshold]

        # Sort by final score descending
        fused.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return fused[:top_k]

    def _execute_bm25_search(
        self,
        query: str,
        all_chunks: Sequence[Any],
        limit: int,
        current_user: UserModel,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute BM25 sparse keyword ranking over chunk text corpus."""
        if not all_chunks:
            return []

        # Filter candidate chunks for security
        is_admin = self._is_user_admin(current_user)
        valid_chunks = []
        for chunk in all_chunks:
            # Document authorization check
            doc = getattr(chunk, "document", None)
            if doc:
                owner_id = str(getattr(doc, "owner_id", ""))
                visibility = str(getattr(doc, "visibility", "private"))
                if not is_admin and owner_id != str(current_user.id) and visibility != "public":
                    continue

                # Filter criteria
                if filters:
                    if filters.get("document_id") and str(doc.id) != str(filters["document_id"]):
                        continue
                    if filters.get("mime_type") and doc.mime_type != filters["mime_type"]:
                        continue
                    if filters.get("language") and hasattr(doc, "content_record") and doc.content_record:
                        if doc.content_record.language != filters["language"]:
                            continue

            valid_chunks.append(chunk)

        if not valid_chunks:
            return []

        corpus_tokens = [_tokenize(chunk.content) for chunk in valid_chunks]
        query_tokens = _tokenize(query)

        if not query_tokens or not any(corpus_tokens):
            return []

        if BM25_AVAILABLE and BM25Okapi is not None:
            bm25 = BM25Okapi(corpus_tokens)
            scores = bm25.get_scores(query_tokens)
        else:
            # Fallback term frequency scorer
            scores = []
            q_set = set(query_tokens)
            for c_tokens in corpus_tokens:
                tf = sum(1 for t in c_tokens if t in q_set)
                scores.append(float(tf))

        results = []
        max_score = max(scores) if scores and max(scores) > 0 else 1.0
        for chunk, score in zip(valid_chunks, scores):
            if score <= 0:
                continue
            norm_score = float(score / max_score)
            doc = getattr(chunk, "document", None)
            results.append({
                "id": str(chunk.id),
                "score": norm_score,
                "payload": {
                    "chunk_id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "owner_id": str(doc.owner_id) if doc else str(current_user.id),
                    "chunk_index": chunk.chunk_index,
                    "page_number": getattr(chunk, "page_number", 1),
                    "text_snippet": chunk.content,
                    "visibility": str(doc.visibility) if doc else "private",
                    "mime_type": str(doc.mime_type) if doc else "text/plain",
                    "original_filename": str(doc.original_filename) if doc else "",
                },
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def _reciprocal_rank_fusion(
        self,
        semantic_list: list[dict[str, Any]],
        keyword_list: list[dict[str, Any]],
        rrf_k: int = 60,
    ) -> list[dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF) algorithm.

        RRF_score(d) = sum( 1 / (rrf_k + rank(d)) ) for each system rank list.
        """
        rrf_scores: dict[str, float] = {}
        payload_map: dict[str, dict[str, Any]] = {}

        # Process Semantic list
        for rank, item in enumerate(semantic_list, start=1):
            chunk_id = item["id"]
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (rrf_k + rank))
            payload_map[chunk_id] = item.get("payload", {})

        # Process Keyword list
        for rank, item in enumerate(keyword_list, start=1):
            chunk_id = item["id"]
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (rrf_k + rank))
            if chunk_id not in payload_map:
                payload_map[chunk_id] = item.get("payload", {})

        # Normalize final RRF scores to [0, 1] range
        max_rrf = max(rrf_scores.values()) if rrf_scores else 1.0

        fused_results = []
        for chunk_id, score in rrf_scores.items():
            norm_score = float(score / max_rrf) if max_rrf > 0 else 0.0
            fused_results.append({
                "id": chunk_id,
                "score": round(norm_score, 4),
                "payload": payload_map[chunk_id],
            })

        fused_results.sort(key=lambda x: x["score"], reverse=True)
        return fused_results

    def _build_security_filters(
        self,
        current_user: UserModel,
        custom_filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Construct Qdrant query payload filters enforcing ownership & RBAC."""
        filters: dict[str, Any] = {}

        is_admin = self._is_user_admin(current_user)
        if not is_admin:
            # Non-admins can access owned documents OR public documents
            filters["owner_id"] = str(current_user.id)

        if custom_filters:
            for k in ("document_id", "mime_type", "language", "visibility"):
                if custom_filters.get(k):
                    filters[k] = str(custom_filters[k])

        return filters

    def _is_user_admin(self, user: UserModel) -> bool:
        """Check if user has administrative privileges."""
        if not hasattr(user, "roles") or not user.roles:
            return False
        role_names = {r.name.upper() for r in user.roles}
        return bool(role_names.intersection({"ADMIN", "MANAGER", "SUPER_ADMIN"}))
