from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from typing import Optional
import asyncio
import json
import time
import httpx
from core.rotation import (
    run_with_fallback,
    REGISTRY,
    mark_used,
    mark_failed,
    record_latency,
    CIRCUITS,
    CircuitState,
)
from cache.manager import get as cache_get, set as cache_set
from core.config import CFG

router = APIRouter()

SEARCH_TTL = CFG.get("cache", {}).get("ttl_search", 3600)
FETCH_TTL = CFG.get("cache", {}).get("ttl_fetch", 1800)


@router.get("/search")
async def search(
    q: str = Query(...),
    max_results: int = Query(5, ge=1, le=20),
    backend: Optional[str] = Query(None),
    no_cache: bool = Query(False),
):
    key = f"search:{q}:{max_results}"
    if not no_cache:
        cached = await cache_get(key, ttl=SEARCH_TTL)
        if cached:
            cached["cached"] = True
            return cached
    if backend and backend in REGISTRY:
        cb = CIRCUITS.get(backend)
        if cb and not cb.can_execute():
            return {
                "results": [],
                "error": f"Backend '{backend}' circuit is open",
                "backend_used": backend,
            }
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                results = await asyncio.wait_for(
                    REGISTRY[backend]["fn"](q, max_results, client), timeout=12
                )
            elapsed_ms = (time.monotonic() - start) * 1000
            record_latency(backend, elapsed_ms)
            if results:
                mark_used(backend)
                result = {
                    "results": results,
                    "backend_used": backend,
                    "tried": [backend],
                    "query": q,
                    "cached": False,
                }
            else:
                mark_failed(backend)
                result = {
                    "results": [],
                    "error": "Backend returned no results",
                    "backend_used": backend,
                    "tried": [backend],
                    "query": q,
                    "cached": False,
                }
        except Exception:
            elapsed_ms = (time.monotonic() - start) * 1000
            record_latency(backend, elapsed_ms)
            mark_failed(backend)
            result = {
                "results": [],
                "error": f"Backend '{backend}' failed",
                "backend_used": backend,
                "tried": [backend],
                "query": q,
                "cached": False,
            }
    else:
        result = await run_with_fallback(q, max_results)
        result.update({"query": q, "cached": False})
    await cache_set(key, result, ttl=SEARCH_TTL)
    return result


@router.get("/search/all")
async def search_all(q: str = Query(...), max_results: int = Query(3, ge=1, le=10)):
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = {}
        for name, data in REGISTRY.items():
            cb = CIRCUITS.get(name)
            if cb and not cb.can_execute():
                continue
            tasks[name] = asyncio.create_task(
                asyncio.wait_for(data["fn"](q, max_results, client), timeout=12)
            )
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
    seen, merged = set(), []
    for name, result in zip(tasks.keys(), gathered):
        if isinstance(result, Exception):
            mark_failed(name)
            continue
        mark_used(name)
        for r in result:
            if r["url"] not in seen:
                seen.add(r["url"])
                merged.append(r)
    return {
        "query": q,
        "results": merged,
        "total": len(merged),
        "backends_queried": list(tasks.keys()),
    }


@router.get("/search/stream")
async def search_stream(q: str = Query(...), max_results: int = Query(5, ge=1, le=20)):
    async def event_generator():
        key = f"search:{q}:{max_results}"
        cached = await cache_get(key, ttl=SEARCH_TTL)
        if cached:
            yield f"data: {json.dumps({'event': 'cached', 'results': cached['results'], 'backend': cached.get('backend_used', 'cache')})}\n\n"
            return

        seen_urls = set()
        merged = []
        async with httpx.AsyncClient(follow_redirects=True) as client:
            task_map = {}
            for name, data in REGISTRY.items():
                cb = CIRCUITS.get(name)
                if cb and not cb.can_execute():
                    continue
                task_map[name] = asyncio.create_task(
                    asyncio.wait_for(data["fn"](q, max_results, client), timeout=12)
                )

            for done in asyncio.as_completed(task_map.values()):
                name = None
                for n, t in task_map.items():
                    if t is done:
                        name = n
                        break
                start = time.monotonic()
                try:
                    results = await done
                    elapsed_ms = (time.monotonic() - start) * 1000
                    record_latency(name, elapsed_ms)
                    if results:
                        mark_used(name)
                        new_results = []
                        for r in results:
                            if r["url"] not in seen_urls:
                                seen_urls.add(r["url"])
                                new_results.append(r)
                                merged.append(r)
                        if new_results:
                            yield f"data: {json.dumps({'event': 'results', 'backend': name, 'results': new_results, 'total_so_far': len(merged)})}\n\n"
                    else:
                        mark_failed(name)
                        yield f"data: {json.dumps({'event': 'backend_empty', 'backend': name})}\n\n"
                except Exception as e:
                    elapsed_ms = (time.monotonic() - start) * 1000
                    record_latency(name, elapsed_ms)
                    mark_failed(name)
                    yield f"data: {json.dumps({'event': 'backend_error', 'backend': name, 'error': str(e)})}\n\n"

        yield f"data: {json.dumps({'event': 'done', 'total': len(merged), 'query': q})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
