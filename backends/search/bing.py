from core.rotation import register
from core.agents import random_headers
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from backends.search.base import SearchResult


@register("bing_scrape", weight=1.0)
async def search(query: str, max_results: int, client):
    url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max_results}"
    r = await client.get(url, headers=random_headers(), timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for res in soup.select("li.b_algo")[:max_results]:
        t = res.select_one("h2 a")
        s = res.select_one(".b_caption p")
        if t:
            out.append(
                SearchResult(
                    title=t.get_text(strip=True),
                    url=t.get("href", ""),
                    snippet=s.get_text(strip=True) if s else "",
                    source="bing",
                ).model_dump()
            )
    return out
