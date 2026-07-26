"""
Summarization Service Module
============================

Domain service generating document summaries (Short, Detailed, Executive, Bullet),
Key Takeaways, and Suggested Questions using the LLM Service provider.

Architectural Rationale:
- Clean Architecture & SOLID design principles.
- Single Responsibility Principle: Focuses exclusively on prompt construction and JSON response parsing for document summaries.
- Reuses `LLMService` without duplicating model inference logic.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class SummarizationService:
    """Enterprise Document Summarization Service."""

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def generate_summary(
        self,
        text_content: str,
        summary_type: str = "executive",
        include_takeaways: bool = True,
        generate_questions: bool = True,
    ) -> dict[str, Any]:
        """
        Generate structured document summary with key takeaways and optional suggested questions.

        Args:
            text_content: Full or chunked document text.
            summary_type: short | detailed | executive | bullet
            include_takeaways: Whether to extract key takeaways.
            generate_questions: Whether to generate key questions answered by document.

        Returns:
            Structured dictionary containing summary, type, takeaways, and questions.
        """
        system_prompt = (
            "You are an expert enterprise document intelligence assistant for BlackRock. "
            "Your task is to analyze document text and produce structured summaries in valid JSON format only.\n"
            "Do not include markdown code fences or conversational text outside the JSON object.\n"
            "JSON structure required:\n"
            "{\n"
            '  "summary": "Summary text string",\n'
            '  "summary_type": "type_string",\n'
            '  "key_takeaways": ["Takeaway 1", "Takeaway 2"],\n'
            '  "suggested_questions": ["Question 1", "Question 2"]\n'
            "}"
        )

        user_prompt = (
            f"DOCUMENT CONTENT:\n{text_content[:12000]}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Generate a high-quality '{summary_type.lower()}' summary of the document.\n"
            f"- short: 2-3 concise sentences.\n"
            f"- detailed: Thorough multi-paragraph overview.\n"
            f"- executive: Strategic executive briefing focusing on core decisions, financial/operational implications, and risk factors.\n"
            f"- bullet: 5-8 bulleted statements.\n"
            f"2. {'Include 3-5 critical key takeaways.' if include_takeaways else 'Provide empty list for key_takeaways.'}\n"
            f"3. {'Generate 3 key analytical questions answered by this document.' if generate_questions else 'Provide empty list for suggested_questions.'}\n"
            f"Output strictly valid JSON matching the requested schema."
        )

        response = await self.llm_service.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
        )

        parsed = self._parse_json_response(response.content)

        return {
            "summary": parsed.get("summary", response.content),
            "summary_type": summary_type.lower(),
            "key_takeaways": parsed.get("key_takeaways", []),
            "suggested_questions": parsed.get("suggested_questions", []),
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
            logger.warning("Failed to parse LLM JSON summary output: %s", str(exc))
            return {"summary": content}
