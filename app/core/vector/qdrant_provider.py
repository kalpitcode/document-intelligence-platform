"""
Qdrant Vector Storage Provider Module
====================================

Enterprise integration with Qdrant vector database for document chunk embeddings.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles.
- Handles collection initialization (`documents` collection with Cosine metric).
- Provides an in-memory vector fallback when Qdrant server is unreachable or in testing mode,
  mirroring the pattern used in MinIOStorageProvider.
- Enforces strict metadata payload filtering (ownership, visibility, mime_type, date, tags, language).
"""

from __future__ import annotations

import logging
import os
import math
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Try importing qdrant_client
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as rest_models
    QDRANT_AVAILABLE = True
except ImportError:
    QdrantClient = None
    rest_models = None
    QDRANT_AVAILABLE = False


# In-memory vector storage fallback dictionary:
# Key: collection_name -> List of point dicts: {"id": str, "vector": list[float], "payload": dict}
_memory_vector_store: dict[str, list[dict[str, Any]]] = {}


def _cosine_similarity(vec_a: Any, vec_b: Any) -> float:
    """Calculate cosine similarity between two vectors safely (supports lists and numpy arrays)."""
    if vec_a is None or vec_b is None:
        return 0.0
    a_list = vec_a.tolist() if hasattr(vec_a, "tolist") else vec_a
    b_list = vec_b.tolist() if hasattr(vec_b, "tolist") else vec_b
    if not a_list or not b_list or len(a_list) != len(b_list):
        return 0.0
    dot = sum(a * b for a, b in zip(a_list, b_list))
    norm_a = math.sqrt(sum(a * a for a in a_list))
    norm_b = math.sqrt(sum(b * b for b in b_list))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class QdrantProvider:
    """
    Qdrant Vector Store Provider Class.

    Manages connection, collection initialization, vector upserts, metadata filtering,
    and cosine similarity vector retrieval.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        api_key: str | None = None,
        collection_name: str = "documents",
    ) -> None:
        settings = get_settings()
        self.host = host or getattr(settings, "qdrant_host", "localhost")
        self.port = port or getattr(settings, "qdrant_port", 6333)
        self.api_key = api_key or getattr(settings, "qdrant_api_key", None)
        self.collection_name = collection_name

        self.client: Any = None
        self._is_online: bool = False
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Qdrant client and verify connection."""
        settings = get_settings()
        is_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        if not QDRANT_AVAILABLE or QdrantClient is None or getattr(settings, "app_env", "") in ("testing", "test") or is_pytest:
            self._is_online = False
            logger.info("Qdrant client unavailable or in testing mode, using in-memory vector store fallback")
            return

        try:
            self.client = QdrantClient(
                host=self.host,
                port=self.port,
                api_key=self.api_key,
                timeout=2.0,
            )
            # Ping collections
            self.client.get_collections()
            self._is_online = True
            logger.info("Qdrant vector provider initialized", extra={"host": self.host, "port": self.port})
        except Exception as exc:
            self._is_online = False
            logger.warning("Qdrant connection failed, using in-memory vector store fallback: %s", str(exc))

    async def ensure_collection(
        self,
        collection_name: str | None = None,
        vector_size: int = 384,
    ) -> bool:
        """Ensure collection exists in Qdrant or memory store."""
        name = collection_name or self.collection_name
        if self._is_online and self.client and rest_models:
            try:
                collections = self.client.get_collections().collections
                exists = any(c.name == name for c in collections)
                if not exists:
                    self.client.create_collection(
                        collection_name=name,
                        vectors_config=rest_models.VectorParams(
                            size=vector_size,
                            distance=rest_models.Distance.COSINE,
                        ),
                    )
                return True
            except Exception as exc:
                logger.error("Error creating Qdrant collection '%s': %s", name, str(exc))
                return False

        # In-memory store ensure
        if name not in _memory_vector_store:
            _memory_vector_store[name] = []
        return True

    async def upsert_points(
        self,
        points: list[dict[str, Any]],
        collection_name: str | None = None,
    ) -> bool:
        """
        Upsert a list of point dictionaries into Qdrant or memory store.

        Each point dict must contain:
        - `id`: str (UUID)
        - `vector`: list[float]
        - `payload`: dict[str, Any]
        """
        name = collection_name or self.collection_name
        if not points:
            return True

        if self._is_online and self.client and rest_models:
            try:
                qdrant_points = [
                    rest_models.PointStruct(
                        id=p["id"],
                        vector=p["vector"],
                        payload=p["payload"],
                    )
                    for p in points
                ]
                self.client.upsert(
                    collection_name=name,
                    points=qdrant_points,
                )
                return True
            except Exception as exc:
                logger.error("Failed to upsert vectors into Qdrant: %s", str(exc))
                return False

        # In-memory store fallback
        if name not in _memory_vector_store:
            _memory_vector_store[name] = []

        store = _memory_vector_store[name]
        for p in points:
            # Replace existing point if ID matches
            store[:] = [item for item in store if item["id"] != p["id"]]
            store.append({
                "id": p["id"],
                "vector": p["vector"],
                "payload": p["payload"],
            })
        return True

    async def search_vectors(
        self,
        query_vector: list[float] | Any,
        limit: int = 20,
        filters: dict[str, Any] | None = None,
        score_threshold: float | None = None,
        collection_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute vector similarity search with payload filtering.

        Returns list of match dicts: `{"id": str, "score": float, "payload": dict}`.
        """
        if hasattr(query_vector, "tolist"):
            query_vector = query_vector.tolist()

        name = collection_name or self.collection_name
        if self._is_online and self.client and rest_models:
            try:
                # Build Qdrant filter
                qdrant_filter = None
                if filters:
                    conditions = []
                    for key, value in filters.items():
                        if value is not None:
                            if isinstance(value, list):
                                conditions.append(
                                    rest_models.FieldCondition(
                                        key=key,
                                        match=rest_models.MatchAny(any=value),
                                    )
                                )
                            else:
                                conditions.append(
                                    rest_models.FieldCondition(
                                        key=key,
                                        match=rest_models.MatchValue(value=value),
                                    )
                                )
                    if conditions:
                        qdrant_filter = rest_models.Filter(must=conditions)

                search_res = self.client.search(
                    collection_name=name,
                    query_vector=query_vector,
                    limit=limit,
                    query_filter=qdrant_filter,
                    score_threshold=score_threshold,
                )

                return [
                    {
                        "id": str(hit.id),
                        "score": float(hit.score),
                        "payload": hit.payload or {},
                    }
                    for hit in search_res
                ]
            except Exception as exc:
                logger.error("Qdrant vector search query failed: %s", str(exc))

        # In-memory vector store fallback search
        store = _memory_vector_store.get(name, [])
        matches = []
        for item in store:
            payload = item["payload"]
            # Apply filters if provided
            if filters:
                match_filter = True
                for f_key, f_val in filters.items():
                    if f_val is not None:
                        val_in_payload = payload.get(f_key)
                        if isinstance(f_val, list):
                            str_list = [str(x) for x in f_val]
                            if str(val_in_payload) not in str_list:
                                match_filter = False
                                break
                        elif str(val_in_payload) != str(f_val):
                            match_filter = False
                            break
                if not match_filter:
                    continue

            score = _cosine_similarity(query_vector, item["vector"])
            if score_threshold is not None and score < score_threshold:
                continue

            matches.append({
                "id": item["id"],
                "score": score,
                "payload": payload,
            })

        # Sort by similarity score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:limit]

    async def delete_vectors_by_document_id(
        self,
        document_id: str,
        collection_name: str | None = None,
    ) -> int:
        """Delete all vector points belonging to a specific document."""
        name = collection_name or self.collection_name
        if self._is_online and self.client and rest_models:
            try:
                self.client.delete(
                    collection_name=name,
                    points_selector=rest_models.FilterSelector(
                        filter=rest_models.Filter(
                            must=[
                                rest_models.FieldCondition(
                                    key="document_id",
                                    match=rest_models.MatchValue(value=document_id),
                                )
                            ]
                        )
                    ),
                )
                return 1
            except Exception as exc:
                logger.error("Failed to delete vectors for doc '%s' from Qdrant: %s", document_id, str(exc))
                return 0

        # Memory store fallback delete
        if name in _memory_vector_store:
            initial_count = len(_memory_vector_store[name])
            _memory_vector_store[name] = [
                p for p in _memory_vector_store[name]
                if p["payload"].get("document_id") != document_id
            ]
            return initial_count - len(_memory_vector_store[name])
        return 0
