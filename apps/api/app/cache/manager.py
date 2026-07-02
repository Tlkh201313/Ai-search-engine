"""Cache facade — selects a backend from settings, exposes a single instance."""

from __future__ import annotations

import hashlib
from typing import Any

from app.cache.base import CacheBackend
from app.cache.memory import MemoryCache
from app.cache.sqlite import SQLiteCache
from app.config import settings
from app.logging import get_logger

log = get_logger("cache")


def make_key(*parts: Any) -> str:
    """Stable cache key from arbitrary parts."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


class CacheManager:
    def __init__(self) -> None:
        self._backend: CacheBackend | None = None

    async def init(self) -> None:
        if self._backend is not None:
            return
        if settings.cache_backend == "memory":
            self._backend = MemoryCache()
        else:
            try:
                backend: CacheBackend = SQLiteCache(settings.cache_db_path)
                await backend.init()
                self._backend = backend
                log.info("cache: sqlite at %s", settings.cache_db_path)
                return
            except Exception as exc:  # pragma: no cover - defensive
                log.warning("cache: sqlite unavailable (%s), falling back to memory", exc)
                self._backend = MemoryCache()
        await self._backend.init()

    async def _b(self) -> CacheBackend:
        if self._backend is None:
            await self.init()
        assert self._backend is not None
        return self._backend

    async def get(self, key: str) -> Any | None:
        try:
            return await (await self._b()).get(key)
        except Exception as exc:  # pragma: no cover - cache never breaks a request
            log.warning("cache get failed: %s", exc)
            return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        try:
            await (await self._b()).set(key, value, ttl)
        except Exception as exc:  # pragma: no cover
            log.warning("cache set failed: %s", exc)

    async def delete(self, key: str) -> None:
        await (await self._b()).delete(key)

    async def clear(self) -> int:
        return await (await self._b()).clear()

    async def count(self) -> int:
        return await (await self._b()).count()

    async def close(self) -> None:
        if self._backend is not None:
            await self._backend.close()
            self._backend = None


cache = CacheManager()
