"""Multi-provider web search (free / no-key by default)."""

from app.search import bing, brave, duckduckgo, mojeek, searxng, wikipedia  # noqa: F401
from app.search.aggregator import multi_search, search_query
from app.search.base import PROVIDERS

__all__ = ["multi_search", "search_query", "PROVIDERS"]
