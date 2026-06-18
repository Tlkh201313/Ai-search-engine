"""
SQLite cache backend.

Stores JSON-serialized values keyed by string, each row carrying an absolute
``expires_at`` timestamp so expiry is decided at read time and a background
sweeper can evict stale rows. The connection is opened lazily on first use,
so callers never have to worry about whether :func:`init` has run yet.
"""

import asyncio
import json
import pathlib
import time
from typing import Any, Optional

import aiosqlite

from core.config import CFG

DEFAULT_TTL = int(CFG.get("cache", {}).get("ttl_search", 3600))
EVICT_INTERVAL = int(CFG.get("cache", {}).get("evict_interval", 300))

DB_PATH = pathlib.Path(CFG.get("cache", {}).get("db_path", "cache/search.db"))

_db: Optional[aiosqlite.Connection] = None
_init_lock = asyncio.Lock()


async def init() -> None:
    """Open the connection and create the table. Safe to call repeatedly."""
    global _db
    if _db is not None:
        return
    async with _init_lock:
        if _db is not None:  # double-checked: another coroutine won the race
            return
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        db = await aiosqlite.connect(str(DB_PATH))
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                expires_at REAL NOT NULL
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at)"
        )
        await db.commit()
        _db = db


async def _conn() -> aiosqlite.Connection:
    if _db is None:
        await init()
    assert _db is not None
    return _db


async def get(key: str, ttl: int = DEFAULT_TTL) -> Optional[Any]:
    """Return the cached value, or ``None`` if missing or expired.

    ``ttl`` is accepted for API symmetry; expiry is governed by the
    ``expires_at`` written at :func:`set` time.
    """
    db = await _conn()
    async with db.execute(
        "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
    ) as cursor:
        row = await cursor.fetchone()
    if row is None:
        return None
    value, expires_at = row
    if expires_at is not None and time.time() > expires_at:
        await db.execute("DELETE FROM cache WHERE key = ?", (key,))
        await db.commit()
        return None
    return json.loads(value)


async def set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    db = await _conn()
    expires_at = time.time() + ttl
    await db.execute(
        "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
        (key, json.dumps(value), expires_at),
    )
    await db.commit()


async def clear() -> None:
    db = await _conn()
    await db.execute("DELETE FROM cache")
    await db.commit()


async def get_entry_count() -> int:
    db = await _conn()
    async with db.execute("SELECT COUNT(*) FROM cache") as cursor:
        row = await cursor.fetchone()
    return int(row[0]) if row else 0


async def _evict_expired() -> int:
    """Delete every expired row. Returns the number removed."""
    db = await _conn()
    cursor = await db.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),))
    await db.commit()
    return cursor.rowcount or 0


async def evict_loop(interval: int = EVICT_INTERVAL) -> None:
    """Background task: periodically sweep expired rows."""
    while True:
        await asyncio.sleep(interval)
        try:
            await _evict_expired()
        except Exception:
            # Eviction is best-effort; never let it kill the loop.
            pass


async def close() -> None:
    global _db
    if _db is not None:
        await _db.close()
        _db = None
