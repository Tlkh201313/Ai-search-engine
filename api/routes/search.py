from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio
import json
import time
import httpx
from core.rotation import (
    run_with_fallback,
    REGISTRY,
    mark_attempt,
    mark_used,
    mark_failed,
    record_latency,
    CIRCUITS,
    REQUEST_TIMEOUT,
)
from cache.manager import get as cache_get, set as cache_set
from core.config import CFG
from core import pipeline

router = APIRouter()

SEARCH_TTL = CFG.get("cache", {}).get("ttl_search", 3600)
STRATEGY = CFG.get("rotation", {}).get("strategy", "lru")


def _cache_key(q: str, max_results: int) -> str:
    return f"search:{q}:{max_results}"


async def _call_backend(name: str, q: str, max_results: int, client) -> list:
    """Invoke a single backend with timeout + metric bookkeeping. Returns the
    result list (possibly empty); raises on failure so callers can record it."""
    start = time.monotonic()
    mark_attempt(name)
    try:
        results = await asyncio.wait_for(
            REGISTRY[name]["fn"](q, max_results, client), timeout=REQUEST_TIMEOUT
        )
    except Exception:
        record_latency(name, (time.monotonic() - start) * 1000)
        mark_failed(name)
        raise
    record_latency(name, (time.monotonic() - start) * 1000)
    if results:
        mark_used(name)
    else:
        mark_failed(name)
    return results or []


@router.get("/search")
async def search(
    q: str = Query(...),
    max_results: int = Query(5, ge=1, le=20),
    backend: Optional[str] = Query(None),
    no_cache: bool = Query(False),
):
    key = _cache_key(q, max_results)
    if not no_cache:
        cached = await cache_get(key, ttl=SEARCH_TTL)
        if cached:
            cached["cached"] = True
            return cached
        semantic = await pipeline.semantic_lookup(q, ttl=SEARCH_TTL)
        if semantic:
            return semantic

    if backend and backend in REGISTRY:
        cb = CIRCUITS.get(backend)
        if cb and not cb.can_execute():
            return {
                "results": [],
                "error": f"Backend '{backend}' circuit is open",
                "backend_used": backend,
                "tried": [backend],
                "query": q,
                "cached": False,
            }
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                results = await _call_backend(backend, q, max_results, client)
            except Exception:
                return {
                    "results": [],
                    "error": f"Backend '{backend}' failed",
                    "backend_used": backend,
                    "tried": [backend],
                    "query": q,
                    "cached": False,
                }
        if not results:
            return {
                "results": [],
                "error": "Backend returned no results",
                "backend_used": backend,
                "tried": [backend],
                "query": q,
                "cached": False,
            }
        result = {
            "results": results,
            "backend_used": backend,
            "tried": [backend],
            "query": q,
            "cached": False,
        }
    else:
        result = await run_with_fallback(q, max_results, strategy=STRATEGY)
        result.update({"query": q, "cached": False})

    if result.get("results"):
        result["results"] = await pipeline.rerank(q, result["results"])
        # Only cache genuine hits — never poison the cache with empty/error
        # responses from a transient backend outage.
        await cache_set(key, result, ttl=SEARCH_TTL)
        await pipeline.semantic_store(q, result, ttl=SEARCH_TTL)
    return result


@router.get("/search/all")
async def search_all(q: str = Query(...), max_results: int = Query(3, ge=1, le=10)):
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = {}
        for name in REGISTRY:
            cb = CIRCUITS.get(name)
            if cb and not cb.can_execute():
                continue
            tasks[name] = asyncio.create_task(
                _call_backend(name, q, max_results, client)
            )
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
    seen, merged = set(), []
    for name, result in zip(tasks.keys(), gathered):
        if isinstance(result, Exception):
            continue
        for r in result:
            url = r.get("url")
            if url and url not in seen:
                seen.add(url)
                merged.append(r)
    merged = await pipeline.rerank(q, merged)
    return {
        "query": q,
        "results": merged,
        "total": len(merged),
        "backends_queried": list(tasks.keys()),
    }


@router.get("/search/stream")
async def search_stream(q: str = Query(...), max_results: int = Query(5, ge=1, le=20)):
    async def event_generator():
        key = _cache_key(q, max_results)
        cached = await cache_get(key, ttl=SEARCH_TTL)
        if cached:
            payload = {
                "event": "cached",
                "results": cached["results"],
                "backend": cached.get("backend_used", "cache"),
            }
            yield f"data: {json.dumps(payload)}\n\n"
            return

        seen_urls = set()
        merged = []

        async def run_one(name, client):
            """Wrap a backend call so the completed future carries its own
            name — ``asyncio.as_completed`` does not preserve task identity."""
            try:
                results = await _call_backend(name, q, max_results, client)
                return name, results, None
            except Exception as e:
                return name, None, e

        async with httpx.AsyncClient(follow_redirects=True) as client:
            tasks = []
            for name in REGISTRY:
                cb = CIRCUITS.get(name)
                if cb and not cb.can_execute():
                    continue
                tasks.append(asyncio.create_task(run_one(name, client)))

            for fut in asyncio.as_completed(tasks):
                name, results, err = await fut
                if err is not None:
                    payload = {
                        "event": "backend_error",
                        "backend": name,
                        "error": str(err),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    continue
                if not results:
                    yield f"data: {json.dumps({'event': 'backend_empty', 'backend': name})}\n\n"
                    continue
                new_results = []
                for r in results:
                    url = r.get("url")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        new_results.append(r)
                        merged.append(r)
                if new_results:
                    payload = {
                        "event": "results",
                        "backend": name,
                        "results": new_results,
                        "total_so_far": len(merged),
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

        if merged:
            await cache_set(
                key,
                {"results": merged, "backend_used": "stream", "query": q},
                ttl=SEARCH_TTL,
            )
        yield f"data: {json.dumps({'event': 'done', 'total': len(merged), 'query': q})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
