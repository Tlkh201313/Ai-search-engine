"""Concurrent multi-provider search with per-provider isolation and dedup."""

from __future__ import annotations

import asyncio
import time

import httpx

from app.cache import cache
from app.cache.manager import make_key
from app.config import settings
from app.logging import get_logger
from app.models import SearchResult
from app.search.base import PROVIDERS
from app.textutil import normalize_url

log = get_logger("search")

_PROVIDER_TIMEOUT = 10.0


async def search_query(
    query: str,
    providers: list[str],
    limit: int,
    client: httpx.AsyncClient,
) -> list[SearchResult]:
    """Run one query across the given providers concurrently."""
    active = [p for p in providers if p in PROVIDERS]
    if not active:
        return []

    async def _run(name: str) -> list[SearchResult]:
        start = time.monotonic()
        try:
            results = await asyncio.wait_for(
                PROVIDERS[name]["fn"](query, limit, client), timeout=_PROVIDER_TIMEOUT
            )
            log.info("provider %s -> %d results (%dms)", name, len(results),
                     int((time.monotonic() - start) * 1000))
            return results
        except Exception as exc:
            log.warning("provider %s failed: %s", name, exc)
            return []

    gathered = await asyncio.gather(*(_run(name) for name in active))
    merged: list[SearchResult] = []
    for batch in gathered:
        merged.extend(batch)
    return merged


async def multi_search(
    queries: list[str],
    providers: list[str] | None = None,
    limit: int = 8,
    use_cache: bool = True,
) -> list[SearchResult]:
    """Search several queries, merge, and dedupe by normalized URL."""
    providers = providers or settings.search_providers
    cache_key = make_key("search", sorted(queries), sorted(providers), limit)
    if use_cache:
        cached = await cache.get(cache_key)
        if cached is not None:
            return [SearchResult(**r) for r in cached]

    async with httpx.AsyncClient(follow_redirects=True, timeout=settings.fetch_timeout) as client:
        batches = await asyncio.gather(
            *(search_query(q, providers, limit, client) for q in queries)
        )

    seen: set[str] = set()
    deduped: list[SearchResult] = []
    for batch in batches:
        for result in batch:
            key = normalize_url(result.url)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(result)

    if use_cache and deduped:
        await cache.set(
            cache_key, [r.model_dump() for r in deduped], ttl=settings.cache_ttl_search
        )
    return deduped
