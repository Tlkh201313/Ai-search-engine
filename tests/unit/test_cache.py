"""Test SQLite cache with TTL and eviction."""

import pytest
import pytest_asyncio
import time
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

from cache import sqlite_cache


@pytest_asyncio.fixture(autouse=True)
async def clean_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_cache.db"
    monkeypatch.setattr(sqlite_cache, "DB_PATH", db_path)
    monkeypatch.setattr(sqlite_cache, "_db", None)
    await sqlite_cache.init()
    yield
    if sqlite_cache._db is not None:
        await sqlite_cache.close()


@pytest.mark.asyncio
class TestSQLiteCache:
    async def test_set_and_get(self):
        await sqlite_cache.set("key1", {"data": "value"})
        assert await sqlite_cache.get("key1") == {"data": "value"}

    async def test_get_missing_returns_none(self):
        assert await sqlite_cache.get("nonexistent") is None

    async def test_ttl_expires(self):
        await sqlite_cache.set("key1", {"data": "value"}, ttl=1)
        time.sleep(1.1)
        assert await sqlite_cache.get("key1", ttl=1) is None

    async def test_custom_ttl(self):
        await sqlite_cache.set("key1", {"data": "value"}, ttl=10)
        assert await sqlite_cache.get("key1", ttl=10) == {"data": "value"}

    async def test_clear(self):
        await sqlite_cache.set("key1", "a")
        await sqlite_cache.set("key2", "b")
        await sqlite_cache.clear()
        assert await sqlite_cache.get("key1") is None
        assert await sqlite_cache.get("key2") is None

    async def test_get_entry_count(self):
        await sqlite_cache.set("a", 1)
        await sqlite_cache.set("b", 2)
        assert await sqlite_cache.get_entry_count() == 2

    async def test_eviction_removes_expired(self):
        await sqlite_cache.set("expired", "old", ttl=1)
        await sqlite_cache.set("fresh", "new", ttl=9999)
        time.sleep(1.1)
        await sqlite_cache._evict_expired()
        assert await sqlite_cache.get("expired", ttl=1) is None
        assert await sqlite_cache.get("fresh", ttl=9999) == "new"
