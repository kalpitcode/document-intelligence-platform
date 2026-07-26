"""
Unit Tests for LLM Provider Abstraction
=======================================

Tests for LLMProvider, OpenAIProvider, LLMProviderFactory, and bounds validation.
"""

import pytest
from app.core.exceptions.base import ValidationException
from app.core.llm.base import LLMResponse
from app.core.llm.factory import LLMProviderFactory
from app.core.llm.openai_provider import OpenAIProvider


@pytest.mark.asyncio
async def test_llm_provider_factory_instantiation():
    """Verify LLMProviderFactory instantiates OpenAIProvider correctly."""
    provider = LLMProviderFactory.get_provider(
        provider_name="openai",
        model_name="gpt-4o-mini",
        timeout=15.0,
    )
    assert isinstance(provider, OpenAIProvider)
    assert provider.model_name == "gpt-4o-mini"
    assert provider.timeout == 15.0


def test_llm_parameter_bounds_validation():
    """Verify parameter bounds validation for temperature and max_tokens."""
    provider = OpenAIProvider()

    # Temperature validation
    with pytest.raises(ValidationException):
        provider.validate_parameters(temperature=-0.1, max_tokens=100)

    with pytest.raises(ValidationException):
        provider.validate_parameters(temperature=1.5, max_tokens=100)

    # Max tokens validation
    with pytest.raises(ValidationException):
        provider.validate_parameters(temperature=0.0, max_tokens=0)

    with pytest.raises(ValidationException):
        provider.validate_parameters(temperature=0.0, max_tokens=200000)

    # Valid parameters pass without exception
    provider.validate_parameters(temperature=0.0, max_tokens=1000)


@pytest.mark.asyncio
async def test_openai_provider_mock_completion():
    """Verify OpenAIProvider generates grounded fallback completion when API key is unconfigured."""
    provider = OpenAIProvider(model_name="gpt-4o-mini")

    prompt = "ENTERPRISE DOCUMENT CONTEXT: [Doc: Report.pdf, Page: 1] BlackRock revenue grew by 10%. USER QUESTION: What was the growth rate?"
    response: LLMResponse = await provider.generate_completion(
        prompt=prompt,
        system_prompt="Answer strictly using provided context.",
        temperature=0.0,
        max_tokens=200,
    )

    assert isinstance(response, LLMResponse)
    assert len(response.content) > 0
    assert response.prompt_tokens > 0
    assert response.completion_tokens > 0
    assert response.total_tokens == response.prompt_tokens + response.completion_tokens
    assert response.latency_ms >= 0
