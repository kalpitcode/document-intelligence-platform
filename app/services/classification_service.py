"""
Classification Service Module
==============================

Domain service for automated document categorization, topic classification, and confidence scoring.

Architectural Rationale:
- Clean Architecture & SOLID design principles.
- Structured JSON output with deterministic confidence evaluation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ClassificationService:
    """Enterprise Document Classification Service."""

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def classify_document(self, text_content: str) -> dict[str, Any]:
        """
        Classify document category, identify primary/secondary topics, and output confidence score.

        Returns:
            Dictionary containing category, topics, confidence, and model execution metrics.
        """
        system_prompt = (
            "You are an enterprise AI document classifier for BlackRock's Aladdin platform. "
            "Analyze the document text and output a structured JSON classification payload.\n"
            "Output JSON format:\n"
            "{\n"
            '  "category": "Document Category",\n'
            '  "primary_topic": "Main Topic",\n'
            '  "secondary_topics": ["Topic 1", "Topic 2"],\n'
            '  "confidence_score": 0.95,\n'
            '  "reasoning": "Brief categorization rationale"\n'
            "}"
        )

        user_prompt = (
            f"DOCUMENT CONTENT SNIPPET:\n{text_content[:10000]}\n\n"
            "Classify this document into standard financial/enterprise categories (e.g., Financial Report, Legal Contract, Regulatory Filing, Investment Memorandum, Operations Policy, Technical Specification, General Corporate).\n"
            "Return valid JSON only."
        )

        response = await self.llm_service.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
        )

        parsed = self._parse_json_response(response.content)

        return {
            "category": parsed.get("category", "General Corporate"),
            "primary_topic": parsed.get("primary_topic", "General Information"),
            "secondary_topics": parsed.get("secondary_topics", []),
            "confidence_score": float(parsed.get("confidence_score", 0.85)),
            "reasoning": parsed.get("reasoning", "Document text analysis"),
            "model_used": response.model_name,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
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
            logger.warning("Failed to parse LLM classification JSON output: %s", str(exc))
            return {"category": "General Corporate", "confidence_score": 0.70}
