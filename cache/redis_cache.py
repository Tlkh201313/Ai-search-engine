"""
Redis cache backend.

A drop-in alternative to :mod:`cache.sqlite_cache` with the same async API.
Values are JSON-serialized and stored under a key prefix; expiry is delegated
to Redis' native per-key TTL, so there is nothing to sweep. ``redis`` is an
optional dependency — importing this module without it raises a clear error.
"""

import json
import os
from typing import Any, Optional

try:
    import redis.asyncio as aioredis

    AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    aioredis = None
    AVAILABLE = False

from core.config import CFG

DEFAULT_TTL = int(CFG.get("cache", {}).get("ttl_search", 3600))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
KEY_PREFIX = "aisearch:"

_client = None


async def init() -> None:
    global _client
    if _client is not None:
        return
    if not AVAILABLE:
        raise RuntimeError(
            "Redis backend selected but 'redis' is not installed. "
            "Run: pip install redis  (or set [cache] backend = \"sqlite\")"
        )
    _client = aioredis.from_url(REDIS_URL, decode_responses=True)


async def _conn():
    if _client is None:
        await init()
    return _client


def _k(key: str) -> str:
    return f"{KEY_PREFIX}{key}"


async def get(key: str, ttl: int = DEFAULT_TTL) -> Optional[Any]:
    client = await _conn()
    raw = await client.get(_k(key))
    if raw is None:
        return None
    return json.loads(raw)


async def set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    client = await _conn()
    await client.set(_k(key), json.dumps(value), ex=ttl)


async def clear() -> None:
    client = await _conn()
    keys = [k async for k in client.scan_iter(match=f"{KEY_PREFIX}*")]
    if keys:
        await client.delete(*keys)


async def get_entry_count() -> int:
    client = await _conn()
    count = 0
    async for _ in client.scan_iter(match=f"{KEY_PREFIX}*"):
        count += 1
    return count


async def _evict_expired() -> int:
    # Redis evicts expired keys automatically; nothing to do.
    return 0


async def evict_loop(interval: int = 300) -> None:  # pragma: no cover
    # No-op loop kept for API symmetry with the SQLite backend.
    return


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
