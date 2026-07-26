"""
Unit Tests for Enterprise AI Feature Services
=============================================

Verifies domain services (Summarization, Classification, Extraction, Translation, Analysis)
with mocked LLM Service responses.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.services.analysis_service import AnalysisService
from app.services.classification_service import ClassificationService
from app.services.extraction_service import ExtractionService
from app.core.llm.base import LLMResponse
from app.services.llm_service import LLMService
from app.services.summarization_service import SummarizationService
from app.services.translation_service import TranslationService


@pytest.fixture
def mock_llm_service() -> MagicMock:
    """Fixture providing mocked LLMService."""
    service = MagicMock(spec=LLMService)
    service.generate = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_summarization_service_executive_summary(mock_llm_service: MagicMock) -> None:
    """Test SummarizationService generates executive summary payload."""
    json_output = '{"summary": "BlackRock Q4 earnings grew by 15%.", "summary_type": "executive", "key_takeaways": ["Revenue up"], "suggested_questions": ["What is target ROI?"]}'
    mock_llm_service.generate.return_value = LLMResponse(
        content=json_output,
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        model_name="mock-gpt4",
        latency_ms=100,
        estimated_cost=0.002,
    )

    svc = SummarizationService(mock_llm_service)
    result = await svc.generate_summary("Q4 Financial Report sample text", summary_type="executive")

    assert result["summary"] == "BlackRock Q4 earnings grew by 15%."
    assert result["summary_type"] == "executive"
    assert "Revenue up" in result["key_takeaways"]
    assert len(result["suggested_questions"]) == 1


@pytest.mark.asyncio
async def test_classification_service(mock_llm_service: MagicMock) -> None:
    """Test ClassificationService categorizes document correctly."""
    json_output = '{"category": "Financial Report", "primary_topic": "Earnings", "secondary_topics": ["Revenue", "Dividends"], "confidence_score": 0.96, "reasoning": "Financial tables present"}'
    mock_llm_service.generate.return_value = LLMResponse(
        content=json_output,
        prompt_tokens=80,
        completion_tokens=40,
        total_tokens=120,
        model_name="mock-gpt4",
        latency_ms=100,
        estimated_cost=0.001,
    )

    svc = ClassificationService(mock_llm_service)
    result = await svc.classify_document("Annual Financial Statement content")

    assert result["category"] == "Financial Report"
    assert result["confidence_score"] == 0.96
    assert "Revenue" in result["secondary_topics"]


@pytest.mark.asyncio
async def test_extraction_service(mock_llm_service: MagicMock) -> None:
    """Test ExtractionService extracts entities and action items."""
    json_output = '{"keywords": ["Aladdin", "RAG"], "entities": {"people": ["Larry Fink"], "organizations": ["BlackRock"], "locations": ["New York"], "dates": ["2026-07-26"]}, "action_items": [{"description": "Review portfolio risk", "assignee": "Risk Team", "deadline": "2026-08-01"}]}'
    mock_llm_service.generate.return_value = LLMResponse(
        content=json_output,
        prompt_tokens=110,
        completion_tokens=60,
        total_tokens=170,
        model_name="mock-gpt4",
        latency_ms=100,
        estimated_cost=0.003,
    )

    svc = ExtractionService(mock_llm_service)
    result = await svc.extract_information("Larry Fink at BlackRock New York presented portfolio updates on 2026-07-26.")

    assert "Aladdin" in result["keywords"]
    assert "Larry Fink" in result["entities"]["people"]
    assert len(result["action_items"]) == 1
    assert result["action_items"][0]["assignee"] == "Risk Team"


@pytest.mark.asyncio
async def test_translation_service(mock_llm_service: MagicMock) -> None:
    """Test TranslationService translates document text."""
    json_output = '{"translated_text": "Informe financiero anual", "source_language": "English", "target_language": "Spanish"}'
    mock_llm_service.generate.return_value = LLMResponse(
        content=json_output,
        prompt_tokens=50,
        completion_tokens=30,
        total_tokens=80,
        model_name="mock-gpt4",
        latency_ms=100,
        estimated_cost=0.001,
    )

    svc = TranslationService(mock_llm_service)
    result = await svc.translate_document("Annual financial report", target_language="Spanish")

    assert result["translated_text"] == "Informe financiero anual"
    assert result["target_language"] == "Spanish"


@pytest.mark.asyncio
async def test_analysis_service(mock_llm_service: MagicMock) -> None:
    """Test AnalysisService sentiment analysis and text statistics."""
    json_output = '{"sentiment": "positive", "sentiment_score": 0.88, "writing_style": "Executive", "readability_score": "High", "key_observations": ["Strong growth outlook"]}'
    mock_llm_service.generate.return_value = LLMResponse(
        content=json_output,
        prompt_tokens=90,
        completion_tokens=45,
        total_tokens=135,
        model_name="mock-gpt4",
        latency_ms=100,
        estimated_cost=0.002,
    )

    svc = AnalysisService(mock_llm_service)
    sample_text = "The investment portfolio experienced extraordinary revenue growth this quarter. Strategic decisions yielded high returns."
    result = await svc.analyze_document(sample_text)

    assert result["sentiment"] == "positive"
    assert result["sentiment_score"] == 0.88
    assert result["statistics"]["word_count"] > 10
    assert result["statistics"]["sentence_count"] == 2
