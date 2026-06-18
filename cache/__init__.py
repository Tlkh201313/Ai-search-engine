"""
Cache package.

Two interchangeable backends — SQLite (default, zero-config) and Redis —
sit behind a single async facade in ``cache.manager``. Pick the backend with
``[cache] backend = "sqlite" | "redis"`` in ``config/settings.toml`` or the
``CACHE_BACKEND`` environment variable.

The public API (``init``, ``get``, ``set``, ``clear``, ``get_entry_count``)
is identical across backends so the rest of the app never imports a concrete
implementation directly.
"""
