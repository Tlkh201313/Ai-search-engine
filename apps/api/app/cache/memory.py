"""In-memory TTL cache (fallback / tests). Not shared across processes."""

from __future__ import annotations

import time
from typing import Any


class MemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}

    async def init(self) -> None:  # noqa: D401 - protocol impl
        return None

    async def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.time():
            self._store.pop(key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        self._store[key] = (time.time() + ttl, value)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count

    async def count(self) -> int:
        now = time.time()
        return sum(1 for expires, _ in self._store.values() if expires >= now)

    async def close(self) -> None:
        self._store.clear()
