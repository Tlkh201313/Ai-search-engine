import asyncio

import httpx
import pytest
from httpx import ASGITransport

from app.fetch.fetcher import FetchedPage
from app.main import app
from app.models import ResearchMode, SearchResult
from app.research import pipeline
from app.research.session import ResearchSession

_LONG = (
    "Photosynthesis is the process by which green plants convert light energy into "
    "chemical energy stored in glucose. It occurs in the chloroplasts. " * 15
)


@pytest.fixture(autouse=True)
def _patch_pipeline(monkeypatch):
    async def fake_multi_search(queries, providers=None, limit=8, use_cache=True):
        return [
            SearchResult(title="Photosynthesis", url="https://en.wikipedia.org/wiki/Photosynthesis", provider="wikipedia"),
            SearchResult(title="Bio", url="https://biology.org/photosynthesis", provider="duckduckgo"),
        ]

    async def fake_fetch_many(urls, max_chars=None, concurrency=None):
        return [
            FetchedPage(
                url=u, ok=True, status=200, title="Photosynthesis", domain=u.split("/")[2],
                text=_LONG, word_count=len(_LONG.split()), fetched_at="2024-06-01T00:00:00+00:00",
            )
            for u in urls
        ]

    monkeypatch.setattr(pipeline, "multi_search", fake_multi_search)
    monkeypatch.setattr(pipeline, "fetch_many", fake_fetch_many)


@pytest.mark.asyncio
async def test_run_research_extractive(monkeypatch):
    # No LLM configured -> extractive answer with real citations.
    monkeypatch.setattr(pipeline.llm, "available", lambda: False)
    session = ResearchSession(id="test1", query="what is photosynthesis", mode=ResearchMode.quick)
    result = await pipeline.run_research(session)
    assert result.status == "complete"
    assert result.sources, "expected ranked sources"
    assert result.answer.detail
    assert result.answer.citations, "expected at least one citation"
    # Every citation must map to a real source id.
    valid_ids = {s.id for s in result.sources}
    assert all(c in valid_ids for c in result.answer.citations)


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "llm" in body and "search_providers" in body


@pytest.mark.asyncio
async def test_research_endpoint_end_to_end(monkeypatch):
    monkeypatch.setattr(pipeline.llm, "available", lambda: False)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/api/research", json={"query": "what is photosynthesis", "mode": "quick"}
        )
        assert created.status_code == 200
        rid = created.json()["id"]

        result = None
        for _ in range(50):
            resp = await client.get(f"/api/research/{rid}")
            if resp.status_code == 200:
                result = resp.json()
                break
            await asyncio.sleep(0.05)

        assert result is not None, "research did not complete in time"
        assert result["answer"]["detail"]
        assert result["sources"]

        sources = await client.get(f"/api/sources?research_id={rid}")
        assert sources.status_code == 200
        assert len(sources.json()) == len(result["sources"])


@pytest.mark.asyncio
async def test_settings_endpoint():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/settings")
        assert resp.status_code == 200
        assert "modes" in resp.json()
        assert "quick" in resp.json()["modes"]
