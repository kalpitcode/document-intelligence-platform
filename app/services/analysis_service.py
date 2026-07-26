"""
Analysis Service Module
=======================

Domain service performing Sentiment Analysis, Writing Style Assessment, Readability Index calculation,
and Document Statistics.

Architectural Rationale:
- Clean Architecture & SOLID design principles.
- Combines heuristic text statistics computation with LLM qualitative sentiment analysis.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class AnalysisService:
    """Enterprise Document Analysis & Analytics Service."""

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def analyze_document(self, text_content: str) -> dict[str, Any]:
        """
        Analyze document sentiment, style, readability, and text statistics.

        Returns:
            Dictionary containing sentiment, writing_style, readability, and statistics metrics.
        """
        # 1. Compute deterministic text statistics
        stats = self._compute_text_statistics(text_content)

        # 2. LLM Qualitative Sentiment & Writing Style analysis
        system_prompt = (
            "You are an enterprise document analyst for BlackRock. "
            "Analyze the document text for tone, sentiment, writing style, and readability score.\n"
            "Output JSON Schema:\n"
            "{\n"
            '  "sentiment": "positive | neutral | negative | mixed",\n'
            '  "sentiment_score": 0.85,\n'
            '  "writing_style": "Formal / Technical / Analytical / Executive",\n'
            '  "readability_score": "High / Medium / Low",\n'
            '  "key_observations": ["Observation 1", "Observation 2"]\n'
            "}"
        )

        user_prompt = (
            f"DOCUMENT CONTENT SNIPPET:\n{text_content[:10000]}\n\n"
            "Perform sentiment analysis and evaluate writing style. Output valid JSON only."
        )

        response = await self.llm_service.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
        )

        parsed = self._parse_json_response(response.content)

        return {
            "sentiment": parsed.get("sentiment", "neutral"),
            "sentiment_score": float(parsed.get("sentiment_score", 0.0)),
            "writing_style": parsed.get("writing_style", "Professional/Technical"),
            "readability_level": parsed.get("readability_score", "High"),
            "key_observations": parsed.get("key_observations", []),
            "statistics": stats,
            "model_used": response.model_name,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
        }

    def _compute_text_statistics(self, text: str) -> dict[str, Any]:
        """Calculate deterministic text statistics (word count, sentence count, reading time)."""
        words = re.findall(r"\b\w+\b", text)
        word_count = len(words)
        sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
        sentence_count = max(len(sentences), 1)
        char_count = len(text)

        avg_words_per_sentence = round(word_count / sentence_count, 2)
        # Average adult reading speed: ~200 words per minute
        reading_time_minutes = max(1, round(word_count / 200, 1))

        return {
            "character_count": char_count,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_words_per_sentence": avg_words_per_sentence,
            "estimated_reading_time_minutes": reading_time_minutes,
        }

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """Safely parse LLM JSON output."""
        clean = content.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        try:
            return json.loads(clean)
        except Exception as exc:
            logger.warning("Failed to parse LLM analysis JSON output: %s", str(exc))
            return {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "writing_style": "Professional",
                "readability_score": "Medium",
            }
