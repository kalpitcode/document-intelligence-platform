"""
Prompt Builder Service Module
=============================

Service responsible for constructing enterprise system prompts, formatting context blocks with citation tags,
and enforcing zero-hallucination RAG instructions.

Architectural Rationale:
- Single Responsibility Principle (SRP): Isolates prompt formulation logic from retrieval and generation.
- Strict Enterprise System Directives: Mandates grounding, explicit fallback when information is missing,
  and inline citation tagging.
"""

from __future__ import annotations

from dataclasses import dataclass
import structlog
import tiktoken

from app.services.context_retrieval_service import RetrievedContextChunk

logger = structlog.get_logger(__name__)

DEFAULT_ENTERPRISE_RAG_SYSTEM_PROMPT = """You are an enterprise AI assistant for BlackRock's Aladdin platform.
Your primary directive is to answer user questions using ONLY the provided enterprise document context below.

STRICT RULES & CONSTRAINTS:
1. Answer ONLY using the supplied document context. Do not use outside knowledge or extrapolate beyond the text.
2. If the requested information is not present in the context, explicitly state: "The requested information is not present in the provided enterprise documentation."
3. Never fabricate or hallucinate any facts, metrics, or financial figures.
4. Cite every factual statement by referencing the Document Name and Page Number supplied in the context (e.g., [Document: Q4_Report.pdf, Page: 5]).
5. Maintain maximum accuracy, professional tone, and strict confidentiality."""


@dataclass(frozen=True)
class FormattedPromptEnvelope:
    """Dataclass holding system prompt, user prompt, and total prompt token count."""

    system_prompt: str
    user_prompt: str
    prompt_tokens: int
    template_name: str = "default_rag"
    template_version: str = "1.0.0"


class PromptBuilderService:
    """Service building enterprise grounded RAG prompts."""

    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        try:
            self.tokenizer = tiktoken.get_encoding(encoding_name)
        except Exception:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Calculate exact token count using tiktoken."""
        if not text:
            return 0
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            return len(text) // 4

    def format_context_blocks(self, chunks: list[RetrievedContextChunk]) -> str:
        """Format retrieved context chunks into structured citation blocks."""
        if not chunks:
            return "No relevant enterprise document context found."

        context_blocks = []
        for idx, chunk in enumerate(chunks, start=1):
            page_str = f"Page {chunk.page_number}" if chunk.page_number else "Page N/A"
            header = f"[SOURCE {idx} | Document: {chunk.document_name} | {page_str} | Chunk: {chunk.chunk_id}]"
            block = f"{header}\n{chunk.text}\n"
            context_blocks.append(block)

        return "\n---\n".join(context_blocks)

    def build_prompt(
        self,
        user_question: str,
        chunks: list[RetrievedContextChunk],
        custom_system_prompt: str | None = None,
        max_prompt_tokens: int = 4000,
    ) -> FormattedPromptEnvelope:
        """
        Construct system prompt and user context prompt for LLM call.

        Args:
            user_question: Original user query string.
            chunks: Deduplicated, score-filtered context chunks.
            custom_system_prompt: Optional override for default enterprise system prompt.
            max_prompt_tokens: Maximum token limit for the full prompt.

        Returns:
            FormattedPromptEnvelope with system_prompt, user_prompt, and token metrics.
        """
        system_prompt = (custom_system_prompt or DEFAULT_ENTERPRISE_RAG_SYSTEM_PROMPT).strip()

        context_text = self.format_context_blocks(chunks)
        user_prompt = f"ENTERPRISE DOCUMENT CONTEXT:\n{context_text}\n\nUSER QUESTION:\n{user_question}\n\nGROUNDED ANSWER:"

        system_tokens = self.count_tokens(system_prompt)
        user_tokens = self.count_tokens(user_prompt)
        total_prompt_tokens = system_tokens + user_tokens

        # Check total prompt token limit safety
        if total_prompt_tokens > max_prompt_tokens:
            logger.warning(
                "Prompt total tokens exceed safety limit, truncating context text",
                total_prompt_tokens=total_prompt_tokens,
                max_prompt_tokens=max_prompt_tokens,
            )
            # Truncate context if required
            available_user_tokens = max_prompt_tokens - system_tokens - 100
            if available_user_tokens > 200:
                user_prompt_tokens = self.tokenizer.encode(user_prompt)[:available_user_tokens]
                user_prompt = self.tokenizer.decode(user_prompt_tokens)
                total_prompt_tokens = system_tokens + len(user_prompt_tokens)

        template_name = "custom_prompt" if custom_system_prompt else "default_rag"
        return FormattedPromptEnvelope(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prompt_tokens=total_prompt_tokens,
            template_name=template_name,
            template_version="1.0.0",
        )
