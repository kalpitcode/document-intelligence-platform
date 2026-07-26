"""
Embedding Generation Service Module
====================================

Domain service for loading embedding models, batch generating dense float vector representations,
validating vector dimensions, and caching embeddings in Redis.

**Architectural Rationale:**
- Implements Clean Architecture & SOLID principles.
- Uses `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions) for dense text representations.
- Supports single text and batch text vector generation.
- Implements deterministic fallback vector generator for testing/offline environments.
- Integrates with Redis Cache Service to avoid redundant embedding computations.
"""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Any

from app.services.cache_service import CacheService

logger = logging.getLogger(__name__)

# Attempt sentence_transformers import
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False


def _generate_deterministic_vector(text: str, dimension: int = 384) -> list[float]:
    """
    Generate a deterministic, normalized pseudo-random float vector from text content.

    Used when PyTorch/SentenceTransformers is offline or during testing.
    """
    vec = []
    for i in range(dimension):
        seed_str = f"{text}:{i}"
        h_val = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest()[:8], 16)
        val = (h_val / 0xFFFFFFFF) * 2.0 - 1.0
        vec.append(val)

    # Normalize vector to unit length
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


class EmbeddingService:
    """
    Embedding Generation & Model Management Service.

    Loads sentence transformer models, generates embeddings for text chunks,
    validates dimensions, and checks cache.
    """

    DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    DEFAULT_DIMENSION = 384

    def __init__(
        self,
        cache_service: CacheService | None = None,
        model_name: str = DEFAULT_MODEL_NAME,
        dimension: int = DEFAULT_DIMENSION,
    ) -> None:
        self.cache_service = cache_service
        self.model_name = model_name
        self.dimension = dimension
        self.model: Any = None
        self._model_loaded: bool = False

    def load_model(self) -> bool:
        """Load sentence transformer model into memory."""
        if self._model_loaded:
            return True

        if SENTENCE_TRANSFORMERS_AVAILABLE and SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer(self.model_name)
                self._model_loaded = True
                logger.info("SentenceTransformer model loaded successfully: %s", self.model_name)
                return True
            except Exception as exc:
                logger.warning("Failed to load SentenceTransformer model '%s': %s", self.model_name, str(exc))
                self._model_loaded = False
                return False

        logger.info("SentenceTransformers library unavailable, using deterministic vector generator")
        self._model_loaded = False
        return False

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate dense vector embedding for a single text string."""
        clean_text = text.strip()
        if not clean_text:
            return [0.0] * self.dimension

        # Check Redis Cache
        cache_key = f"embedding:{self.model_name}:{hashlib.sha256(clean_text.encode('utf-8')).hexdigest()}"
        if self.cache_service:
            try:
                cached_vec = await self.cache_service.get(cache_key)
                if cached_vec and isinstance(cached_vec, list) and len(cached_vec) == self.dimension:
                    return cached_vec
            except Exception as exc:
                logger.debug("Redis cache fetch failed for embedding: %s", str(exc))

        # Generate vector
        vector = await self._compute_vector(clean_text)

        # Validate dimension
        self.validate_dimension(vector)

        # Store in Redis Cache
        if self.cache_service:
            try:
                await self.cache_service.set(cache_key, vector, ttl=86400)
            except Exception as exc:
                logger.debug("Redis cache store failed for embedding: %s", str(exc))

        return vector

    async def generate_batch_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Batch generate embeddings for multiple text strings."""
        if not texts:
            return []

        embeddings = []
        for text in texts:
            vec = await self.generate_embedding(text)
            embeddings.append(vec)
        return embeddings

    async def _compute_vector(self, text: str) -> list[float]:
        """Compute raw vector representation."""
        if not self._model_loaded:
            self.load_model()

        if self._model_loaded and self.model is not None:
            try:
                raw_vec = self.model.encode(text, convert_to_numpy=True)
                vec_list = raw_vec.tolist() if hasattr(raw_vec, "tolist") else list(raw_vec)
                return [float(x) for x in vec_list]
            except Exception as exc:
                logger.error("Error computing embedding vector via SentenceTransformer: %s", str(exc))

        # Fallback deterministic vector generator
        return _generate_deterministic_vector(text, self.dimension)

    def validate_dimension(self, vector: list[float]) -> None:
        """Validate vector output dimension."""
        if len(vector) != self.dimension:
            raise ValueError(
                f"Embedding vector dimension mismatch: expected {self.dimension}, got {len(vector)}"
            )

    def get_model_info(self) -> dict[str, Any]:
        """Return model metadata status info."""
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "provider": "sentence-transformers" if self._model_loaded else "deterministic-fallback",
            "is_loaded": self._model_loaded,
        }
