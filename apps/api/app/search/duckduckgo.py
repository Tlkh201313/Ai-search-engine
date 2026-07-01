"""DuckDuckGo HTML endpoint (no key). Falls back to the lite endpoint."""

from __future__ import annotations

from urllib.parse import quote_plus

import httpx
from selectolax.parser import HTMLParser

from app.models import SearchResult
from app.search.base import decode_ddg_url, default_headers, register

_HTML = "https://html.duckduckgo.com/html/?q={q}"
_LITE = "https://lite.duckduckgo.com/lite/?q={q}"


@register("duckduckgo", weight=1.2)
async def search(query: str, limit: int, client: httpx.AsyncClient) -> list[SearchResult]:
    results = await _parse_html(query, limit, client)
    if not results:
        results = await _parse_lite(query, limit, client)
    return results


async def _parse_html(query: str, limit: int, client: httpx.AsyncClient) -> list[SearchResult]:
    resp = await client.get(_HTML.format(q=quote_plus(query)), headers=default_headers())
    tree = HTMLParser(resp.text)
    out: list[SearchResult] = []
    for node in tree.css(".result")[: limit * 2]:
        link = node.css_first(".result__a")
        if link is None:
            continue
        href = decode_ddg_url(link.attributes.get("href", "") or "")
        if not href.startswith("http"):
            continue
        snippet_node = node.css_first(".result__snippet")
        out.append(
            SearchResult(
                title=link.text(strip=True),
                url=href,
                snippet=snippet_node.text(strip=True) if snippet_node else "",
                provider="duckduckgo",
            )
        )
        if len(out) >= limit:
            break
    return out


async def _parse_lite(query: str, limit: int, client: httpx.AsyncClient) -> list[SearchResult]:
    resp = await client.get(_LITE.format(q=quote_plus(query)), headers=default_headers())
    tree = HTMLParser(resp.text)
    out: list[SearchResult] = []
    for link in tree.css("a.result-link")[: limit * 2]:
        href = decode_ddg_url(link.attributes.get("href", "") or "")
        if not href.startswith("http"):
            continue
        out.append(
            SearchResult(title=link.text(strip=True), url=href, provider="duckduckgo")
        )
        if len(out) >= limit:
            break
    return out
