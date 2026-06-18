"""
Cache facade.

Selects the concrete backend once at import time (SQLite by default, Redis if
configured) and re-exports its async API. Everything else in the app imports
from here — never from a concrete backend module — so swapping backends is a
one-line config change.
"""

import asyncio
import os
from typing import Any, Optional

from core.config import CFG

_cache_cfg = CFG.get("cache", {})
_backend_name = (os.getenv("CACHE_BACKEND") or _cache_cfg.get("backend", "sqlite")).lower()

if _backend_name == "redis":
    from cache import redis_cache as _impl
else:
    _backend_name = "sqlite"
    from cache import sqlite_cache as _impl

backend_name = _backend_name
_evict_task: Optional[asyncio.Task] = None


async def init() -> None:
    """Initialize the backend and start background eviction."""
    global _evict_task
    await _impl.init()
    if _evict_task is None and hasattr(_impl, "evict_loop"):
        try:
            _evict_task = asyncio.create_task(_impl.evict_loop())
        except RuntimeError:
            # No running loop (e.g. called outside an async context) — skip.
            _evict_task = None


async def get(key: str, ttl: int = 3600) -> Optional[Any]:
    return await _impl.get(key, ttl=ttl)


async def set(key: str, value: Any, ttl: int = 3600) -> None:
    await _impl.set(key, value, ttl=ttl)


async def clear() -> None:
    await _impl.clear()


async def get_entry_count() -> int:
    return await _impl.get_entry_count()


async def shutdown() -> None:
    global _evict_task
    if _evict_task is not None:
        _evict_task.cancel()
        _evict_task = None
    if hasattr(_impl, "close"):
        await _impl.close()
