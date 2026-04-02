from fastapi import APIRouter, Query
from backends.scrape.bs4_scraper import scrape
from cache.manager import get as cache_get, set as cache_set
from core.config import CFG

router = APIRouter()

SCRAPE_TTL = CFG.get("cache", {}).get("ttl_fetch", 1800)


@router.get("/scrape")
async def scrape_page(url: str = Query(...)):
    key = f"scrape:{url}"
    cached = await cache_get(key, ttl=SCRAPE_TTL)
    if cached:
        cached["cached"] = True
        return cached
    result = await scrape(url)
    result["cached"] = False
    await cache_set(key, result, ttl=SCRAPE_TTL)
    return result
