"""SearXNG meta-search (JSON). Uses your own instance when SEARXNG_URL is set.

Run your own for unlimited, key-free meta-search:
    docker run -d -p 8888:8080 searxng/searxng
"""

from __future__ import annotations

import random

import httpx

from app.config import settings
from app.models import SearchResult
from app.search.base import default_headers, register

_PUBLIC = [
    "https://searx.be",
    "https://searx.tiekoetter.com",
    "https://search.rhscz.eu",
]


@register("searxng", weight=1.4)
async def search(query: str, limit: int, client: httpx.AsyncClient) -> list[SearchResult]:
    instance = settings.searxng_url.rstrip("/") or random.choice(_PUBLIC)
    params = {"q": query, "format": "json", "safesearch": "0"}
    resp = await client.get(
        f"{instance}/search", params=params, headers=default_headers()
    )
    resp.raise_for_status()
    data = resp.json()
    out: list[SearchResult] = []
    for item in data.get("results", [])[:limit]:
        url = item.get("url", "")
        if not url:
            continue
        out.append(
            SearchResult(
                title=item.get("title", ""),
                url=url,
                snippet=item.get("content", ""),
                provider="searxng",
                published_at=item.get("publishedDate"),
            )
        )
    return out
