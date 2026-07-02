"""Deduplicate search results and fetched pages."""

from __future__ import annotations

from app.fetch import FetchedPage
from app.models import SearchResult
from app.textutil import jaccard, keywords, normalize_url, title_similarity

_TITLE_DUP_THRESHOLD = 0.90
_CONTENT_DUP_THRESHOLD = 0.85


def dedupe_search_results(results: list[SearchResult]) -> list[SearchResult]:
    """Remove URL duplicates and near-identical titles."""
    seen_urls: set[str] = set()
    kept: list[SearchResult] = []
    for result in results:
        norm = normalize_url(result.url)
        if norm in seen_urls:
            continue
        if any(
            title_similarity(result.title, k.title) >= _TITLE_DUP_THRESHOLD
            for k in kept
            if result.title and k.title
        ):
            continue
        seen_urls.add(norm)
        kept.append(result)
    return kept


def dedupe_pages(pages: list[FetchedPage]) -> list[FetchedPage]:
    """Drop pages whose extracted content is near-duplicate of an earlier one."""
    kept: list[FetchedPage] = []
    fingerprints: list[set[str]] = []
    for page in pages:
        fp = keywords(page.text[:4000])
        if any(jaccard(fp, seen) >= _CONTENT_DUP_THRESHOLD for seen in fingerprints if seen):
            continue
        fingerprints.append(fp)
        kept.append(page)
    return kept
