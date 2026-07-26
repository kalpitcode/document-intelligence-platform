"""
Vector Database Domain Service Module
=====================================

Domain service coordinating Qdrant vector operations, document chunk vector upserts,
deletions, updates, collection initialization, and payload filters.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles.
- Decouples higher-level search orchestration from Qdrant vector store operations.
- Constructs standardized chunk payloads (chunk_id, document_id, owner_id, page_number,
  text_snippet, visibility, mime_type, language, tags).
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.vector.qdrant_provider import QdrantProvider

logger = logging.getLogger(__name__)


class VectorService:
    """
    Vector Database Service.

    Coordinates document chunk vector indexing, similarity queries, updates,
    and deletions in Qdrant.
    """

    def __init__(self, vector_provider: QdrantProvider) -> None:
        self.provider = vector_provider
        self.collection_name = vector_provider.collection_name

    async def initialize_collection(self, vector_size: int = 384) -> bool:
        """Ensure collection exists in Qdrant."""
        return await self.provider.ensure_collection(
            collection_name=self.collection_name,
            vector_size=vector_size,
        )

    async def insert_chunk_vectors(
        self,
        chunk_points: list[dict[str, Any]],
    ) -> bool:
        """
        Upsert a list of chunk points into Qdrant vector collection.

        Points must contain `id`, `vector`, and `payload`.
        """
        if not chunk_points:
            return True

        await self.initialize_collection(vector_size=len(chunk_points[0]["vector"]))
        return await self.provider.upsert_points(
            points=chunk_points,
            collection_name=self.collection_name,
        )

    async def search_similar_chunks(
        self,
        query_vector: list[float],
        limit: int = 20,
        filters: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Execute vector similarity search in Qdrant."""
        await self.initialize_collection(vector_size=len(query_vector))
        return await self.provider.search_vectors(
            query_vector=query_vector,
            limit=limit,
            filters=filters,
            score_threshold=score_threshold,
            collection_name=self.collection_name,
        )

    async def delete_document_vectors(self, document_id: str) -> int:
        """Delete all vectors for a specific document ID."""
        return await self.provider.delete_vectors_by_document_id(
            document_id=str(document_id),
            collection_name=self.collection_name,
        )
