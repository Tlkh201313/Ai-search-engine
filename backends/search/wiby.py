from core.rotation import register
from core.agents import random_headers
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from backends.search.base import SearchResult


@register("wiby", weight=0.5)
async def search(query: str, max_results: int, client):
    url = f"https://wiby.me/?q={quote_plus(query)}"
    r = await client.get(url, headers=random_headers(), timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for res in soup.select("article")[:max_results]:
        t = res.select_one("h2 a")
        s = res.select_one("p")
        if t:
            out.append(
                SearchResult(
                    title=t.get_text(strip=True),
                    url=t.get("href", ""),
                    snippet=s.get_text(strip=True) if s else "",
                    source="wiby",
                ).model_dump()
            )
    return out
