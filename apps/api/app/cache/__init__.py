"""Pluggable async cache (SQLite by default, in-memory fallback)."""

from app.cache.manager import cache

__all__ = ["cache"]
