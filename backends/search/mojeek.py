from core.rotation import register
from core.agents import random_headers
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from backends.search.base import SearchResult


@register("mojeek", weight=0.8)
async def search(query: str, max_results: int, client):
    url = f"https://www.mojeek.com/search?q={quote_plus(query)}&num={max_results}"
    r = await client.get(url, headers=random_headers(), timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for res in soup.select("ul.results li")[:max_results]:
        t = res.select_one("a.title")
        s = res.select_one("p.s")
        if t:
            out.append(
                SearchResult(
                    title=t.get_text(strip=True),
                    url=t.get("href", ""),
                    snippet=s.get_text(strip=True) if s else "",
                    source="mojeek",
                ).model_dump()
            )
    return out
