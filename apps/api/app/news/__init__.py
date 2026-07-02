"""Live news aggregation from public RSS/Atom feeds (no API keys)."""

from app.news.feeds import CATEGORIES, NewsItem, get_news

__all__ = ["CATEGORIES", "NewsItem", "get_news"]
