"""API routers."""

from app.routes import fetch, health, news, research, search, settings, sources

routers = [
    health.router,
    search.router,
    research.router,
    fetch.router,
    sources.router,
    settings.router,
    news.router,
]

__all__ = ["routers"]
