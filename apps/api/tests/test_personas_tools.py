import json

import pytest

from app.fetch.fetcher import FetchedPage
from app.llm import all_personas, get_persona
from app.llm.client import ChatResult, ToolCall
from app.llm.tools import SourceCollector, execute_tool
from app.models import ResearchMode, SearchResult, Source, SourceScores
from app.research import answer as answer_mod
from app.research.modes import get_mode


def _src(i: int, url: str, domain: str, title: str = "T") -> Source:
    return Source(
        id=i, url=url, domain=domain, title=title, excerpt=f"excerpt {title}",
        snippet="snippet", scores=SourceScores(overall=0.7),
    )


# --- Personas -------------------------------------------------------------- #
def test_personas_registry():
    personas = all_personas()
    assert [p.name for p in personas] == ["Solstice", "Lunar", "Tellus", "Zephyr"]
    assert personas[0].tier == 1  # Solstice strongest
    # Zephyr is a fusion; others are single-model.
    assert get_persona("zephyr").fusion is not None
    assert get_persona("solstice").model == "claude-opus"
    # System prompts are distinct and non-trivial, and hide the model identity.
    prompts = {p.name: p.system_prompt for p in personas}
    assert len({*prompts.values()}) == 4
    for name, prompt in prompts.items():
        assert len(prompt) > 200
        assert name in prompt  # persona is told its own name


def test_get_persona_default_and_invalid():
    assert get_persona(None).key == "lunar"  # DEFAULT_PERSONA
    assert get_persona("does-not-exist").key == "lunar"
    assert get_persona("tellus").key == "tellus"


# --- Tools ----------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_read_url_registers_citable_source(monkeypatch):
    page = FetchedPage(
        url="https://new.example/a", ok=True, status=200, title="New", domain="new.example",
        text="readable body content about the topic " * 20, word_count=120,
    )

    async def fake_fetch(url, **kw):
        return page

    monkeypatch.setattr("app.llm.tools.fetch_page", fake_fetch)
    collector = SourceCollector([_src(1, "https://a.com", "a.com")], "topic question")

    out = json.loads(await execute_tool("read_url", {"url": "https://new.example/a"}, collector))
    assert out["id"] == 2
    assert any(s.url == "https://new.example/a" and s.id == 2 for s in collector.sources)

    # Reading the same URL again dedupes to the same id.
    again = json.loads(await execute_tool("read_url", {"url": "https://new.example/a"}, collector))
    assert again["id"] == 2
    assert len(collector.sources) == 2


@pytest.mark.asyncio
async def test_web_search_tool(monkeypatch):
    async def fake_ms(queries, **kw):
        return [SearchResult(title="R", url="https://r.com", snippet="s", provider="x")]

    monkeypatch.setattr("app.llm.tools.multi_search", fake_ms)
    out = json.loads(await execute_tool("web_search", {"query": "q"}, SourceCollector([], "q")))
    assert out["results"][0]["url"] == "https://r.com"


# --- Agentic answer with tools -------------------------------------------- #
@pytest.mark.asyncio
async def test_agent_uses_tools_and_cites_new_source(monkeypatch):
    monkeypatch.setattr(answer_mod.llm, "available", lambda: True)
    page = FetchedPage(
        url="https://doc.example/x", ok=True, status=200, title="Doc", domain="doc.example",
        text="the answer is clearly documented here " * 30, word_count=180,
    )

    async def fake_fetch(url, **kw):
        return page

    monkeypatch.setattr("app.llm.tools.fetch_page", fake_fetch)

    calls = {"n": 0}

    async def fake_chat(messages, model, system=None, tools=None, temperature=0.3, max_tokens=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return ChatResult(
                content="",
                tool_calls=[
                    ToolCall(
                        id="c1", name="read_url", arguments={"url": "https://doc.example/x"},
                        raw={"id": "c1", "type": "function",
                             "function": {"name": "read_url", "arguments": '{"url":"https://doc.example/x"}'}},
                    )
                ],
            )
        return ChatResult(
            content=(
                "## Answer\nThe documented answer holds [2].\n\n"
                "## Details\nGrounded explanation [1][2].\n\n"
                "## Key Takeaways\n- key point [2]\n\n"
                "## Follow-ups\n- what next?"
            ),
            tool_calls=[],
        )

    monkeypatch.setattr(answer_mod.llm, "chat", fake_chat)

    sources = [_src(1, "https://a.com", "a.com")]
    ans, info, final_sources = await answer_mod.generate_answer(
        "the question", get_mode(ResearchMode.quick), sources, persona_key="lunar"
    )
    assert info.grounded is True and info.model == "Lunar"
    assert any(s.id == 2 and s.url == "https://doc.example/x" for s in final_sources)
    assert 2 in ans.citations  # cited the tool-discovered source


@pytest.mark.asyncio
async def test_fusion_persona_runs_and_cites(monkeypatch):
    monkeypatch.setattr(answer_mod.llm, "available", lambda: True)
    seen_models: list[str] = []

    async def fake_chat(messages, model, system=None, tools=None, temperature=0.3, max_tokens=None):
        seen_models.append(model)
        return ChatResult(
            content="## Answer\nFusion answer [1].\n\n## Details\nDetail [1].",
            tool_calls=[],
        )

    monkeypatch.setattr(answer_mod.llm, "chat", fake_chat)
    ans, info, _ = await answer_mod.generate_answer(
        "q", get_mode(ResearchMode.quick), [_src(1, "https://a.com", "a.com")], persona_key="zephyr"
    )
    assert info.model == "Zephyr" and info.grounded is True
    assert 1 in ans.citations
    # Fusion used both the executor (llama) and the planner/checker (haiku) models.
    assert "llama-4-maverick" in seen_models and "claude-3-haiku" in seen_models


@pytest.mark.asyncio
async def test_extractive_fallback_when_unavailable(monkeypatch):
    monkeypatch.setattr(answer_mod.llm, "available", lambda: False)
    ans, info, _ = await answer_mod.generate_answer(
        "q", get_mode(ResearchMode.quick), [_src(1, "https://a.com", "a.com")], persona_key="solstice"
    )
    assert info.grounded is False and info.model == "Solstice"
    assert ans.citations == [1]
