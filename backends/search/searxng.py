"""
SearXNG meta-search. Run your own for truly unlimited:
  docker run -d -p 8888:8080 searxng/searxng
Then set SEARXNG_URL=http://localhost:8888 in .env
"""

import random
from core.rotation import register
from core.agents import random_headers
from urllib.parse import quote_plus
from backends.search.base import SearchResult

PUBLIC_INSTANCES = [
    "https://searx.be",
    "https://search.mdosch.de",
    "https://searx.tiekoetter.com",
    "https://searx.ox2.fr",
]


@register("searxng", weight=1.5)
async def search(query: str, max_results: int, client):
    import os

    local = os.getenv("SEARXNG_URL", "")
    instance = local if local else random.choice(PUBLIC_INSTANCES)
    url = f"{instance}/search?q={quote_plus(query)}&format=json&engines=google,bing,duckduckgo"
    r = await client.get(url, headers=random_headers(), timeout=12)
    data = r.json()
    out = []
    for x in data.get("results", [])[:max_results]:
        out.append(
            SearchResult(
                title=x.get("title", ""),
                url=x.get("url", ""),
                snippet=x.get("content", ""),
                source="searxng",
            ).model_dump()
        )
    return out
