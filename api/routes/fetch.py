from fastapi import APIRouter, Query
from backends.fetch.httpx_fetcher import fetch as httpx_fetch
from cache.manager import get as cache_get, set as cache_set
from core.config import CFG

router = APIRouter()

FETCH_TTL = CFG.get("cache", {}).get("ttl_fetch", 1800)


@router.get("/fetch")
async def fetch_page(
    url: str = Query(...),
    max_chars: int = Query(8000, ge=500, le=50000),
    js_render: bool = Query(False),
):
    key = f"fetch:{url}"
    cached = await cache_get(key, ttl=FETCH_TTL)
    if cached:
        cached["cached"] = True
        return cached
    if js_render:
        try:
            from backends.fetch.playwright_fetcher import fetch
        except Exception:
            fetch = httpx_fetch
    else:
        fetch = httpx_fetch
    result = await fetch(url, max_chars)
    result["cached"] = False
    await cache_set(key, result, ttl=FETCH_TTL)
    return result
