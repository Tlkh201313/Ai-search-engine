"""API routers."""

from app.routes import fetch, health, research, search, settings, sources

routers = [
    health.router,
    search.router,
    research.router,
    fetch.router,
    sources.router,
    settings.router,
]

__all__ = ["routers"]
