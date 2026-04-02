"""Test SQLite cache with TTL and eviction."""

import pytest
import asyncio
import time
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

from cache import sqlite_cache


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test_cache.db"
    monkeypatch.setattr(sqlite_cache, "DB_PATH", db_path)
    monkeypatch.setattr(sqlite_cache, "_db", None)
    asyncio.get_event_loop().run_until_complete(sqlite_cache.init())
    yield
    if sqlite_cache._db:
        asyncio.get_event_loop().run_until_complete(sqlite_cache._db.close())
    sqlite_cache._db = None


class TestSQLiteCache:
    def test_set_and_get(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(sqlite_cache.set("key1", {"data": "value"}))
        result = loop.run_until_complete(sqlite_cache.get("key1"))
        assert result == {"data": "value"}

    def test_get_missing_returns_none(self):
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(sqlite_cache.get("nonexistent"))
        assert result is None

    def test_ttl_expires(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(sqlite_cache.set("key1", {"data": "value"}, ttl=1))
        time.sleep(1.1)
        result = loop.run_until_complete(sqlite_cache.get("key1", ttl=1))
        assert result is None

    def test_custom_ttl(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(sqlite_cache.set("key1", {"data": "value"}, ttl=10))
        result = loop.run_until_complete(sqlite_cache.get("key1", ttl=10))
        assert result == {"data": "value"}

    def test_clear(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(sqlite_cache.set("key1", "a"))
        loop.run_until_complete(sqlite_cache.set("key2", "b"))
        loop.run_until_complete(sqlite_cache.clear())
        r1 = loop.run_until_complete(sqlite_cache.get("key1"))
        r2 = loop.run_until_complete(sqlite_cache.get("key2"))
        assert r1 is None and r2 is None

    def test_get_entry_count(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(sqlite_cache.set("a", 1))
        loop.run_until_complete(sqlite_cache.set("b", 2))
        count = loop.run_until_complete(sqlite_cache.get_entry_count())
        assert count == 2

    def test_eviction_removes_expired(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(sqlite_cache.set("expired", "old", ttl=1))
        loop.run_until_complete(sqlite_cache.set("fresh", "new", ttl=9999))
        time.sleep(1.1)
        loop.run_until_complete(sqlite_cache._evict_expired())
        expired = loop.run_until_complete(sqlite_cache.get("expired", ttl=1))
        fresh = loop.run_until_complete(sqlite_cache.get("fresh", ttl=9999))
        assert expired is None
        assert fresh == "new"
