from core.rotation import register
from core.agents import random_headers
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from backends.search.base import BaseBackend, SearchResult


@register("duckduckgo", weight=1.0)
async def search(query: str, max_results: int, client):
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    r = await client.get(url, headers=random_headers(), timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for res in soup.select(".result")[:max_results]:
        t = res.select_one(".result__title a")
        s = res.select_one(".result__snippet")
        if t:
            out.append(
                SearchResult(
                    title=t.get_text(strip=True),
                    url=t.get("href", ""),
                    snippet=s.get_text(strip=True) if s else "",
                    source="duckduckgo",
                ).model_dump()
            )
    return out
