"""Shared test fixtures.

The SQLite cache opens a background (non-daemon) connection thread on first
use. Under ASGITransport the app's lifespan never runs, so nothing closes it
and the interpreter would hang at exit. Close it explicitly when the session
ends.
"""

import asyncio

import pytest


@pytest.fixture(scope="session", autouse=True)
def _close_cache_connection():
    yield
    try:
        from cache import sqlite_cache

        if sqlite_cache._db is not None:
            asyncio.run(sqlite_cache.close())
    except Exception:
        pass
