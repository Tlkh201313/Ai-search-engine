"""Async SQLite cache with per-entry TTL and lazy eviction."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import aiosqlite


class SQLiteCache:
    def __init__(self, db_path: str) -> None:
        self._path = db_path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        Path(self._path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        await self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                expires_at REAL NOT NULL
            )
            """
        )
        await self._db.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)")
        await self._db.commit()

    async def _conn(self) -> aiosqlite.Connection:
        if self._db is None:
            await self.init()
        assert self._db is not None
        return self._db

    async def get(self, key: str) -> Any | None:
        db = await self._conn()
        async with db.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
        ) as cur:
            row = await cur.fetchone()
        if row is None:
            return None
        value, expires_at = row
        if expires_at < time.time():
            await self.delete(key)
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    async def set(self, key: str, value: Any, ttl: int) -> None:
        db = await self._conn()
        await db.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, json.dumps(value, default=str), time.time() + ttl),
        )
        await db.commit()

    async def delete(self, key: str) -> None:
        db = await self._conn()
        await db.execute("DELETE FROM cache WHERE key = ?", (key,))
        await db.commit()

    async def clear(self) -> int:
        db = await self._conn()
        async with db.execute("SELECT COUNT(*) FROM cache") as cur:
            row = await cur.fetchone()
        await db.execute("DELETE FROM cache")
        await db.commit()
        return int(row[0]) if row else 0

    async def count(self) -> int:
        db = await self._conn()
        await db.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),))
        await db.commit()
        async with db.execute("SELECT COUNT(*) FROM cache") as cur:
            row = await cur.fetchone()
        return int(row[0]) if row else 0

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None
