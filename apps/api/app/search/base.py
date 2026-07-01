"""Search provider registry and shared helpers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from app.models import SearchResult

SearchFn = Callable[[str, int, httpx.AsyncClient], Awaitable[list[SearchResult]]]

# name -> {"fn": callable, "weight": float}
PROVIDERS: dict[str, dict] = {}

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def default_headers() -> dict[str, str]:
    return {
        "User-Agent": _UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def register(name: str, weight: float = 1.0):
    def decorator(fn):
        PROVIDERS[name] = {"fn": fn, "weight": weight}
        return fn

    return decorator


def decode_ddg_url(href: str) -> str:
    """DuckDuckGo HTML wraps targets in /l/?uddg=<encoded>; unwrap them."""
    if not href:
        return href
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        qs = parse_qs(parsed.query)
        target = qs.get("uddg", [None])[0]
        if target:
            return unquote(target)
    return href
