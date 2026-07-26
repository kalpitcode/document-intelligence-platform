"""
Extraction Service Module
=========================

Domain service for extracting Keywords, Named Entities (People, Organizations, Locations, Dates),
and Action Items from enterprise documents.

Architectural Rationale:
- Clean Architecture & SOLID design principles.
- High precision structured entity extraction.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ExtractionService:
    """Enterprise Information Extraction Service."""

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def extract_information(
        self,
        text_content: str,
        extract_entities: bool = True,
        extract_keywords: bool = True,
        extract_action_items: bool = True,
    ) -> dict[str, Any]:
        """
        Extract named entities, keywords, and action items from document text.

        Returns:
            Dictionary containing extracted entities, keywords, action_items, and token metrics.
        """
        system_prompt = (
            "You are an AI information extraction engine for BlackRock. "
            "Extract structured information from document text and output strictly valid JSON.\n"
            "Required JSON Schema:\n"
            "{\n"
            '  "keywords": ["keyword1", "keyword2"],\n'
            '  "entities": {\n'
            '    "people": ["Name 1"],\n'
            '    "organizations": ["Org 1"],\n'
            '    "locations": ["Location 1"],\n'
            '    "dates": ["Date 1"]\n'
            "  },\n"
            '  "action_items": [\n'
            '    {"description": "Action text", "assignee": "Person/Role or Unassigned", "deadline": "Date or N/A"}\n'
            "  ]\n"
            "}"
        )

        user_prompt = (
            f"DOCUMENT CONTENT:\n{text_content[:12000]}\n\n"
            f"INSTRUCTIONS:\n"
            f"- {'Extract top 10 relevant keywords/phrases.' if extract_keywords else 'Keywords list empty.'}\n"
            f"- {'Extract named entities categorized into people, organizations, locations, and dates.' if extract_entities else 'Entities dict empty.'}\n"
            f"- {'Extract explicit or implied action items, tasks, deadlines, and responsibilities.' if extract_action_items else 'Action items list empty.'}\n"
            "Return valid JSON matching the schema."
        )

        response = await self.llm_service.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
        )

        parsed = self._parse_json_response(response.content)

        return {
            "keywords": parsed.get("keywords", []),
            "entities": parsed.get(
                "entities",
                {"people": [], "organizations": [], "locations": [], "dates": []},
            ),
            "action_items": parsed.get("action_items", []),
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
            logger.warning("Failed to parse LLM extraction JSON output: %s", str(exc))
            return {
                "keywords": [],
                "entities": {"people": [], "organizations": [], "locations": [], "dates": []},
                "action_items": [],
            }
