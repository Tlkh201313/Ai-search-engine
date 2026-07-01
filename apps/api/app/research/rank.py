"""Score and rank fetched pages into citable sources."""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime

from app.fetch import FetchedPage
from app.models import Source, SourceScores
from app.research.modes import ModeConfig
from app.textutil import keywords, truncate_words

# Curated domain reputation signals (not exhaustive — a prior, not a verdict).
_HIGH_TRUST = {
    "wikipedia.org", "britannica.com", "nature.com", "science.org", "arxiv.org",
    "ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov", "who.int", "nih.gov", "nasa.gov",
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "nytimes.com",
    "theguardian.com", "economist.com", "ft.com", "bloomberg.com",
    "github.com", "stackoverflow.com", "developer.mozilla.org", "docs.python.org",
    "gov.uk", "europa.eu",
}
_MED_TRUST = {
    "medium.com", "dev.to", "techcrunch.com", "theverge.com", "wired.com",
    "arstechnica.com", "cnbc.com", "forbes.com", "businessinsider.com",
}
_LOW_TRUST = {"pinterest.com", "quora.com", "facebook.com", "reddit.com"}

_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass
    match = _ISO_RE.search(text)
    if match:
        try:
            return datetime.fromisoformat(match.group())
        except ValueError:
            return None
    return None


def _freshness_score(published_at: str | None) -> float:
    dt = _parse_date(published_at)
    if dt is None:
        return 0.4  # unknown date -> neutral
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    age_days = max(0.0, (datetime.now(UTC) - dt).total_seconds() / 86400)
    # ~30-day half-life decay.
    return round(math.exp(-age_days / 45.0), 4)


def _quality_score(domain: str, mode: ModeConfig, word_count: int) -> float:
    base = 0.5
    if any(domain == d or domain.endswith("." + d) for d in _HIGH_TRUST):
        base = 0.95
    elif any(domain == d or domain.endswith("." + d) for d in _MED_TRUST):
        base = 0.65
    elif any(domain == d or domain.endswith("." + d) for d in _LOW_TRUST):
        base = 0.3
    if domain.endswith((".gov", ".edu", ".ac.uk")):
        base = max(base, 0.9)
    if any(domain == d or domain.endswith("." + d) for d in mode.prefer_domains):
        base = min(1.0, base + 0.25)
    if word_count < 120:
        base *= 0.7
    return round(min(1.0, base), 4)


def _depth_score(word_count: int) -> float:
    if word_count <= 0:
        return 0.0
    return round(min(1.0, math.log10(word_count + 1) / math.log10(2500)), 4)


def _relevance_score(query_kw: set[str], title: str, text: str) -> float:
    if not query_kw:
        return 0.5
    title_kw = keywords(title)
    body_kw = keywords(text[:6000])
    title_hit = len(query_kw & title_kw) / len(query_kw)
    body_hit = len(query_kw & body_kw) / len(query_kw)
    return round(min(1.0, 0.6 * body_hit + 0.4 * title_hit), 4)


def build_excerpt(query: str, text: str, max_words: int = 220) -> str:
    """Pick the passages most relevant to the query to send to the LLM."""
    query_kw = keywords(query)
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if len(p.strip()) > 40]
    if not paragraphs:
        return truncate_words(text, max_words)
    scored = []
    for para in paragraphs:
        overlap = len(query_kw & keywords(para))
        scored.append((overlap, para))
    scored.sort(key=lambda x: x[0], reverse=True)
    chosen: list[str] = []
    words = 0
    for overlap, para in scored:
        if overlap == 0 and chosen:
            break
        chosen.append(para)
        words += len(para.split())
        if words >= max_words:
            break
    if not chosen:
        chosen = paragraphs[:2]
    return truncate_words("\n\n".join(chosen), max_words)


def rank_pages(query: str, pages: list[FetchedPage], mode: ModeConfig) -> list[Source]:
    """Score readable pages and return them as ordered, citable sources."""
    query_kw = keywords(query)
    w = mode.weights
    scored: list[tuple[float, Source]] = []
    for page in pages:
        if not page.ok or not page.text:
            continue
        relevance = _relevance_score(query_kw, page.title, page.text)
        freshness = _freshness_score(page.published_at)
        quality = _quality_score(page.domain, mode, page.word_count)
        depth = _depth_score(page.word_count)
        overall = (
            w["relevance"] * relevance
            + w["freshness"] * freshness
            + w["quality"] * quality
            + w["depth"] * depth
        )
        source = Source(
            id=0,
            url=page.url,
            title=page.title or page.domain,
            domain=page.domain,
            snippet=(page.description or page.text[:280]).strip(),
            excerpt=build_excerpt(query, page.text),
            author=page.author,
            description=page.description,
            published_at=page.published_at,
            fetched_at=page.fetched_at,
            favicon=f"https://www.google.com/s2/favicons?domain={page.domain}&sz=64",
            provider="web",
            word_count=page.word_count,
            scores=SourceScores(
                relevance=relevance,
                freshness=freshness,
                quality=quality,
                depth=depth,
                overall=round(overall, 4),
            ),
        )
        scored.append((overall, source))

    scored.sort(key=lambda x: x[0], reverse=True)
    ranked = _diversify([s for _, s in scored], mode.max_sources)
    for idx, source in enumerate(ranked, start=1):
        source.id = idx
    return ranked


def _diversify(sources: list[Source], limit: int, max_per_domain: int = 2) -> list[Source]:
    """Prefer a spread of domains, but backfill so single-domain sets still fill up."""
    picked: list[Source] = []
    overflow: list[Source] = []
    counts: dict[str, int] = {}
    for source in sources:
        if counts.get(source.domain, 0) < max_per_domain:
            picked.append(source)
            counts[source.domain] = counts.get(source.domain, 0) + 1
        else:
            overflow.append(source)
        if len(picked) >= limit:
            return picked[:limit]
    for source in overflow:  # relax the cap only if we still have room
        if len(picked) >= limit:
            break
        picked.append(source)
    return picked[:limit]
