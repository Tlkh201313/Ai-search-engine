from urllib.parse import quote

import httpx
import pytest
import respx

from app.models import SearchResult
from app.search.aggregator import multi_search, search_query
from app.search.base import PROVIDERS, decode_ddg_url

_DDG_HTML = f"""
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg={quote('https://example.com/a', safe='')}">Result A</a>
  <a class="result__snippet">Snippet A about the topic.</a>
</div>
<div class="result">
  <a class="result__a" href="https://example.org/b">Result B</a>
  <a class="result__snippet">Snippet B.</a>
</div>
"""


def test_decode_ddg_url():
    wrapped = f"//duckduckgo.com/l/?uddg={quote('https://target.com/x', safe='')}&rut=abc"
    assert decode_ddg_url(wrapped) == "https://target.com/x"
    assert decode_ddg_url("https://plain.com/y") == "https://plain.com/y"


@pytest.mark.asyncio
@respx.mock
async def test_duckduckgo_parses_and_decodes():
    respx.get(url__startswith="https://html.duckduckgo.com/html/").mock(
        return_value=httpx.Response(200, text=_DDG_HTML)
    )
    async with httpx.AsyncClient() as client:
        results = await PROVIDERS["duckduckgo"]["fn"]("topic", 5, client)
    urls = [r.url for r in results]
    assert "https://example.com/a" in urls  # decoded from redirect
    assert "https://example.org/b" in urls


@pytest.mark.asyncio
async def test_multi_search_dedupes(monkeypatch):
    async def fake_provider(query, limit, client):
        return [
            SearchResult(title="A", url="https://a.com/x", provider="fake"),
            SearchResult(title="A dup", url="https://www.a.com/x/", provider="fake"),
            SearchResult(title="B", url="https://b.com", provider="fake"),
        ]

    PROVIDERS["_fake"] = {"fn": fake_provider, "weight": 1.0}
    try:
        results = await multi_search(["q"], providers=["_fake"], limit=5, use_cache=False)
    finally:
        PROVIDERS.pop("_fake", None)
    assert len(results) == 2  # a.com deduped by normalized URL


@pytest.mark.asyncio
async def test_search_query_isolates_provider_failure():
    async def boom(query, limit, client):
        raise RuntimeError("provider down")

    async def ok(query, limit, client):
        return [SearchResult(title="ok", url="https://ok.com", provider="ok")]

    PROVIDERS["_boom"] = {"fn": boom, "weight": 1.0}
    PROVIDERS["_ok"] = {"fn": ok, "weight": 1.0}
    try:
        async with httpx.AsyncClient() as client:
            results = await search_query("q", ["_boom", "_ok"], 5, client)
    finally:
        PROVIDERS.pop("_boom", None)
        PROVIDERS.pop("_ok", None)
    assert len(results) == 1 and results[0].url == "https://ok.com"
