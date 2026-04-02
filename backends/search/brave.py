from core.rotation import register
from core.agents import random_headers
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from backends.search.base import SearchResult


@register("brave", weight=1.0)
async def search(query: str, max_results: int, client):
    url = f"https://search.brave.com/search?q={quote_plus(query)}&source=web"
    r = await client.get(url, headers=random_headers(), timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for res in soup.select(".snippet")[:max_results]:
        t = res.select_one(".snippet-title")
        a = res.select_one("a")
        d = res.select_one(".snippet-description")
        if t and a:
            out.append(
                SearchResult(
                    title=t.get_text(strip=True),
                    url=a.get("href", ""),
                    snippet=d.get_text(strip=True) if d else "",
                    source="brave",
                ).model_dump()
            )
    return out
