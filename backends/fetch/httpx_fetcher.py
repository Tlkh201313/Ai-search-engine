"""Default fetcher. Swap for playwright_fetcher.py for JS-rendered pages."""
import httpx
from bs4 import BeautifulSoup
from core.agents import random_headers

STRIP_TAGS = ["script","style","nav","footer","header","aside","form"]

async def fetch(url: str, max_chars: int = 8000) -> dict:
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        r = await client.get(url, headers=random_headers())
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(STRIP_TAGS): tag.decompose()
    lines = [l for l in soup.get_text(separator="\n", strip=True).splitlines() if l.strip()]
    text = "\n".join(lines)[:max_chars]
    return {"url": url, "status": r.status_code, "title": soup.title.string if soup.title else None,
            "text": text, "char_count": len(text), "renderer": "httpx"}
