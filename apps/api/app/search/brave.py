"""Brave Search HTML scrape (optional, opt-in — can be rate-limited)."""

from __future__ import annotations

from urllib.parse import quote_plus

import httpx
from selectolax.parser import HTMLParser

from app.models import SearchResult
from app.search.base import default_headers, register


@register("brave", weight=1.0)
async def search(query: str, limit: int, client: httpx.AsyncClient) -> list[SearchResult]:
    url = f"https://search.brave.com/search?q={quote_plus(query)}&source=web"
    resp = await client.get(url, headers=default_headers())
    tree = HTMLParser(resp.text)
    out: list[SearchResult] = []
    for node in tree.css("div.snippet")[: limit * 2]:
        link = node.css_first("a")
        title = node.css_first(".snippet-title") or link
        desc = node.css_first(".snippet-description")
        if link is None or title is None:
            continue
        href = link.attributes.get("href", "") or ""
        if not href.startswith("http"):
            continue
        out.append(
            SearchResult(
                title=title.text(strip=True),
                url=href,
                snippet=desc.text(strip=True) if desc else "",
                provider="brave",
            )
        )
        if len(out) >= limit:
            break
    return out
