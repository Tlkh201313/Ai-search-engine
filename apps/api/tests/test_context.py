import pytest

from app.models import ConversationTurn
from app.research import pipeline


@pytest.mark.asyncio
async def test_standalone_query_no_context_is_identity(monkeypatch):
    monkeypatch.setattr(pipeline.llm, "available", lambda: False)
    assert await pipeline._standalone_query("what is fastapi", []) == "what is fastapi"


@pytest.mark.asyncio
async def test_standalone_query_uses_heuristic_without_llm(monkeypatch):
    monkeypatch.setattr(pipeline.llm, "available", lambda: False)
    context = [ConversationTurn(query="what is fastapi", answer="A web framework.")]
    resolved = await pipeline._standalone_query("why is it fast?", context)
    # Follow-up is folded together with the prior question for a searchable query.
    assert "fastapi" in resolved.lower()
    assert "why is it fast" in resolved.lower()
