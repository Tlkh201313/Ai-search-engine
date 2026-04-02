"""Structured scraper — returns headings, paragraphs, links, images, meta."""
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from core.agents import random_headers

async def scrape(url: str) -> dict:
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        r = await client.get(url, headers=random_headers())
    soup = BeautifulSoup(r.text, "html.parser")
    meta = {(t.get("name") or t.get("property","")): t.get("content","")
            for t in soup.find_all("meta") if t.get("name") or t.get("property")}
    return {
        "url": url, "status": r.status_code,
        "title": soup.title.string if soup.title else None,
        "meta": meta,
        "headings": [{"level": h.name, "text": h.get_text(strip=True)}
                     for h in soup.find_all(["h1","h2","h3","h4"])[:20]],
        "paragraphs": [p.get_text(strip=True) for p in soup.find_all("p")
                       if len(p.get_text(strip=True)) > 40][:15],
        "links": [{"text": a.get_text(strip=True), "href": urljoin(url, a.get("href",""))}
                  for a in soup.find_all("a", href=True) if a.get_text(strip=True)][:30],
        "images": [{"alt": img.get("alt",""), "src": urljoin(url, img.get("src",""))}
                   for img in soup.find_all("img", src=True)][:10],
    }
