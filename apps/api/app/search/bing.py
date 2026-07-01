"""Bing HTML scrape (optional, opt-in)."""

from __future__ import annotations

from urllib.parse import quote_plus

import httpx
from selectolax.parser import HTMLParser

from app.models import SearchResult
from app.search.base import default_headers, register


@register("bing", weight=0.9)
async def search(query: str, limit: int, client: httpx.AsyncClient) -> list[SearchResult]:
    url = f"https://www.bing.com/search?q={quote_plus(query)}&count={limit}"
    resp = await client.get(url, headers=default_headers())
    tree = HTMLParser(resp.text)
    out: list[SearchResult] = []
    for node in tree.css("li.b_algo")[: limit * 2]:
        link = node.css_first("h2 a")
        if link is None:
            continue
        href = link.attributes.get("href", "") or ""
        if not href.startswith("http"):
            continue
        desc = node.css_first(".b_caption p")
        out.append(
            SearchResult(
                title=link.text(strip=True),
                url=href,
                snippet=desc.text(strip=True) if desc else "",
                provider="bing",
            )
        )
        if len(out) >= limit:
            break
    return out
