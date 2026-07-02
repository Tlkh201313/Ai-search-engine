"""Chat-vs-search router heuristics (no LLM configured in tests)."""

import asyncio

from app.research.pipeline import _needs_search


def test_greeting_is_chat():
    assert asyncio.run(_needs_search("hi", [])) is False
    assert asyncio.run(_needs_search("thanks!", [])) is False
    assert asyncio.run(_needs_search("who are you?", [])) is False


def test_search_intent_is_search():
    assert asyncio.run(_needs_search("latest fusion energy news", [])) is True
    assert asyncio.run(_needs_search("research mRNA vaccines", [])) is True
    # ambiguous + no LLM -> default to search
    assert asyncio.run(_needs_search("how does photosynthesis work", [])) is True
