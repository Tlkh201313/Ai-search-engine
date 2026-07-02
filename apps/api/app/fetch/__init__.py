"""Async page fetching + clean text/metadata extraction."""

from app.fetch.fetcher import FetchedPage, fetch_many, fetch_page

__all__ = ["FetchedPage", "fetch_page", "fetch_many"]
