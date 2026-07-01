"""Wikipedia search via the official REST API (no key, very reliable)."""

from __future__ import annotations

import httpx

from app.models import SearchResult
from app.search.base import register

_API = "https://en.wikipedia.org/w/api.php"


@register("wikipedia", weight=1.0)
async def search(query: str, limit: int, client: httpx.AsyncClient) -> list[SearchResult]:
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": min(limit, 15),
        "format": "json",
        "srprop": "snippet|timestamp",
    }
    # Wikimedia's UA policy 403s generic bot strings; use a descriptive UA with a
    # contact URL as they require.
    resp = await client.get(
        _API,
        params=params,
        headers={"User-Agent": "Lumen-Research/1.0 (+https://github.com/lumen; grounded research engine)"},
    )
    resp.raise_for_status()
    data = resp.json()
    out: list[SearchResult] = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "")
        snippet = _strip_html(item.get("snippet", ""))
        page = title.replace(" ", "_")
        out.append(
            SearchResult(
                title=title,
                url=f"https://en.wikipedia.org/wiki/{page}",
                snippet=snippet,
                provider="wikipedia",
                published_at=item.get("timestamp"),
            )
        )
    return out


def _strip_html(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", text).strip()
