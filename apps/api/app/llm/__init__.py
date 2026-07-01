"""Single server-hosted LLM (Anthropic Messages API compatible)."""

from app.llm.client import LLMClient, llm

__all__ = ["LLMClient", "llm"]
