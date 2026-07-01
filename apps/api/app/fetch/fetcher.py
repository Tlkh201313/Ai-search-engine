"""Async page fetching with SSRF guard, retries, timeout, and caching."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urljoin

import httpx

from app.cache import cache
from app.cache.manager import make_key
from app.config import settings
from app.fetch.extract import extract
from app.logging import get_logger
from app.search.base import default_headers
from app.security.ssrf import UnsafeURLError, validate_url
from app.textutil import domain_of

log = get_logger("fetch")

# One retry only: a page that fails within the timeout twice rarely succeeds a
# third time, and we always over-fetch candidates — so dropping a straggler keeps
# the "reading" stage fast without hurting answer quality.
_MAX_RETRIES = 1
_MAX_REDIRECTS = 4
_MAX_BYTES = 2_500_000  # cap a single page download at ~2.5 MB


@dataclass
class FetchedPage:
    url: str
    ok: bool
    status: int = 0
    title: str = ""
    domain: str = ""
    text: str = ""
    author: str | None = None
    description: str | None = None
    published_at: str | None = None
    fetched_at: str | None = None
    word_count: int = 0
    error: str | None = None

    def to_dict(self) -> dict:
        return self.__dict__.copy()


async def fetch_page(
    url: str,
    client: httpx.AsyncClient | None = None,
    max_chars: int | None = None,
    use_cache: bool = True,
) -> FetchedPage:
    """Fetch and extract a single page. Never raises — returns ok=False on error."""
    max_chars = max_chars or settings.fetch_max_chars
    cache_key = make_key("fetch", url, max_chars)
    if use_cache:
        cached = await cache.get(cache_key)
        if cached is not None:
            return FetchedPage(**cached)

    try:
        safe_url = validate_url(url)
    except UnsafeURLError as exc:
        return FetchedPage(url=url, ok=False, error=f"blocked: {exc}")

    owns_client = client is None
    if owns_client:
        # Redirects are followed manually so every hop is SSRF-validated.
        client = httpx.AsyncClient(follow_redirects=False, timeout=settings.fetch_timeout)
    try:
        page = await _fetch_with_retries(safe_url, client, max_chars)
    finally:
        if owns_client:
            await client.aclose()

    if use_cache and page.ok:
        await cache.set(cache_key, page.to_dict(), ttl=settings.cache_ttl_fetch)
    return page


async def _fetch_with_retries(
    url: str, client: httpx.AsyncClient, max_chars: int
) -> FetchedPage:
    last_error = "unknown error"
    for attempt in range(_MAX_RETRIES + 1):
        try:
            page = await _download(url, client, max_chars)
        except UnsafeURLError as exc:
            return FetchedPage(url=url, ok=False, error=f"blocked redirect: {exc}")
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = str(exc)
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            break
        except Exception as exc:  # pragma: no cover - defensive
            last_error = str(exc)
            break
        # Retry only transient server-side statuses.
        if not page.ok and page.status in (429, 500, 502, 503) and attempt < _MAX_RETRIES:
            last_error = page.error or f"HTTP {page.status}"
            await asyncio.sleep(0.5 * (2**attempt))
            continue
        return page
    return FetchedPage(url=url, ok=False, error=last_error)


async def _download(url: str, client: httpx.AsyncClient, max_chars: int) -> FetchedPage:
    """Single fetch with manual, SSRF-validated redirects and a byte cap."""
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        async with client.stream("GET", current, headers=default_headers()) as resp:
            if resp.is_redirect:
                location = resp.headers.get("location")
                if not location:
                    return FetchedPage(
                        url=current, ok=False, status=resp.status_code,
                        error="redirect without location",
                    )
                current = validate_url(urljoin(current, location))  # may raise UnsafeURLError
                continue
            if resp.status_code >= 400:
                return FetchedPage(
                    url=current, ok=False, status=resp.status_code,
                    error=f"HTTP {resp.status_code}",
                )
            content_type = resp.headers.get("content-type", "")
            if "html" not in content_type and "text" not in content_type:
                return FetchedPage(
                    url=current, ok=False, status=resp.status_code,
                    error=f"unsupported content-type: {content_type}",
                )
            raw = bytearray()
            async for chunk in resp.aiter_bytes():
                raw += chunk
                if len(raw) >= _MAX_BYTES:
                    break
            text = raw.decode(resp.encoding or "utf-8", errors="replace")
            data = extract(text, str(resp.url), max_chars)
            return FetchedPage(
                url=str(resp.url),
                ok=bool(data.text),
                status=resp.status_code,
                title=data.title,
                domain=domain_of(str(resp.url)),
                text=data.text,
                author=data.author,
                description=data.description,
                published_at=data.published_at,
                fetched_at=datetime.now(UTC).isoformat(),
                word_count=len(data.text.split()),
                error=None if data.text else "no readable text",
            )
    return FetchedPage(url=url, ok=False, status=0, error="too many redirects")


async def fetch_many(
    urls: list[str], max_chars: int | None = None, concurrency: int | None = None
) -> list[FetchedPage]:
    """Fetch many pages concurrently, bounded by a semaphore."""
    concurrency = concurrency or settings.fetch_concurrency
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(follow_redirects=False, timeout=settings.fetch_timeout) as client:

        async def _one(u: str) -> FetchedPage:
            async with sem:
                return await fetch_page(u, client=client, max_chars=max_chars)

        return list(await asyncio.gather(*(_one(u) for u in urls)))
