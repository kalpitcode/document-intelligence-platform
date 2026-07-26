"""
Translation Service Module
==========================

Domain service for translating enterprise document content between target languages using LLM provider.

Architectural Rationale:
- Clean Architecture & SOLID design principles.
- Preserves technical terminology, formatting, and mathematical/financial symbols.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class TranslationService:
    """Enterprise Document Translation Service."""

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def translate_document(
        self,
        text_content: str,
        target_language: str,
        source_language: str | None = None,
    ) -> dict[str, Any]:
        """
        Translate document text into target language while preserving technical/financial accuracy.

        Args:
            text_content: Document text to translate.
            target_language: Target language (e.g. 'Spanish', 'French', 'German', 'Japanese', 'Mandarin').
            source_language: Optional source language (defaults to auto-detection).

        Returns:
            Dictionary containing translated text, detected source language, target language, and metrics.
        """
        system_prompt = (
            "You are a high-precision enterprise translator for BlackRock's Aladdin platform. "
            "Translate document text accurately while preserving technical, legal, and financial terms.\n"
            "Return output strictly in JSON format matching schema:\n"
            "{\n"
            '  "translated_text": "Translated text content",\n'
            '  "source_language": "Detected or provided source language",\n'
            '  "target_language": "Target language"\n'
            "}"
        )

        user_prompt = (
            f"SOURCE LANGUAGE: {source_language or 'Auto-detect'}\n"
            f"TARGET LANGUAGE: {target_language}\n\n"
            f"TEXT TO TRANSLATE:\n{text_content[:10000]}\n\n"
            "Produce accurate translation in valid JSON format."
        )

        response = await self.llm_service.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
        )

        parsed = self._parse_json_response(response.content)

        return {
            "translated_text": parsed.get("translated_text", response.content),
            "source_language": parsed.get("source_language", source_language or "Auto-detected"),
            "target_language": target_language,
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
            logger.warning("Failed to parse LLM translation JSON output: %s", str(exc))
            return {"translated_text": content}
