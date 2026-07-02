"""Shared test configuration and fixtures."""

import os

# Force ephemeral cache + no LLM before the app imports settings.
os.environ.setdefault("CACHE_BACKEND", "memory")
os.environ.setdefault("LLM_API_KEY", "")
os.environ.setdefault("SEARCH_PROVIDERS", "duckduckgo,wikipedia")

import pytest  # noqa: E402

from app.fetch.fetcher import FetchedPage  # noqa: E402
from app.models import SearchResult  # noqa: E402


@pytest.fixture
def sample_results() -> list[SearchResult]:
    return [
        SearchResult(title="Python (programming language)", url="https://en.wikipedia.org/wiki/Python", snippet="Python is a language.", provider="wikipedia"),
        SearchResult(title="Python site", url="https://www.python.org/", snippet="Official site.", provider="duckduckgo"),
        SearchResult(title="Dup", url="https://python.org", snippet="dup", provider="bing"),
    ]


@pytest.fixture
def sample_pages() -> list[FetchedPage]:
    long_text = (
        "Python is a high-level, general-purpose programming language. "
        "Its design philosophy emphasizes code readability with significant indentation. "
    ) * 20
    return [
        FetchedPage(
            url="https://en.wikipedia.org/wiki/Python",
            ok=True,
            status=200,
            title="Python (programming language)",
            domain="en.wikipedia.org",
            text=long_text,
            published_at="2024-01-01T00:00:00+00:00",
            word_count=len(long_text.split()),
            fetched_at="2024-06-01T00:00:00+00:00",
        ),
        FetchedPage(
            url="https://www.python.org/",
            ok=True,
            status=200,
            title="Welcome to Python.org",
            domain="python.org",
            text="Python is a programming language that lets you work quickly. " * 15,
            word_count=150,
            fetched_at="2024-06-01T00:00:00+00:00",
        ),
    ]
