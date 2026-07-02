"""Mojeek HTML scrape (optional, opt-in — independent index)."""

from __future__ import annotations

from urllib.parse import quote_plus

import httpx
from selectolax.parser import HTMLParser

from app.models import SearchResult
from app.search.base import default_headers, register


@register("mojeek", weight=0.8)
async def search(query: str, limit: int, client: httpx.AsyncClient) -> list[SearchResult]:
    url = f"https://www.mojeek.com/search?q={quote_plus(query)}"
    resp = await client.get(url, headers=default_headers())
    tree = HTMLParser(resp.text)
    out: list[SearchResult] = []
    for node in tree.css("ul.results-standard li")[: limit * 2]:
        link = node.css_first("a.title") or node.css_first("h2 a")
        if link is None:
            continue
        href = link.attributes.get("href", "") or ""
        if not href.startswith("http"):
            continue
        desc = node.css_first("p.s")
        out.append(
            SearchResult(
                title=link.text(strip=True),
                url=href,
                snippet=desc.text(strip=True) if desc else "",
                provider="mojeek",
            )
        )
        if len(out) >= limit:
            break
    return out
