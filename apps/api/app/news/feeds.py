"""Live news aggregation from public RSS/Atom feeds.

No API keys required: a handful of reputable publisher feeds are fetched
concurrently, parsed (titles, links, thumbnails, timestamps), deduped and
interleaved per source so one publisher never dominates the page. Results are
cached briefly to keep the news page instant and polite to publishers.
"""

from __future__ import annotations

import asyncio
import html
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx

from app.cache import cache
from app.cache.manager import make_key
from app.logging import get_logger
from app.search.base import default_headers
from app.textutil import domain_of

log = get_logger("news")

_TIMEOUT = 8.0
_PER_FEED = 10  # keep at most N items per feed before interleaving
_CACHE_TTL = 600  # 10 minutes — news is "live enough" and feeds stay unhammered

# category -> [(source name, feed url), ...]  All are stable, keyless feeds.
FEEDS: dict[str, list[tuple[str, str]]] = {
    "top": [
        ("BBC News", "https://feeds.bbci.co.uk/news/rss.xml"),
        ("The Guardian", "https://www.theguardian.com/international/rss"),
        ("Sky News", "https://feeds.skynews.com/feeds/rss/home.xml"),
    ],
    "world": [
        ("BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("The Guardian", "https://www.theguardian.com/world/rss"),
        ("Sky News", "https://feeds.skynews.com/feeds/rss/world.xml"),
    ],
    "tech": [
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
        ("BBC News", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ],
    "business": [
        ("BBC News", "https://feeds.bbci.co.uk/news/business/rss.xml"),
        ("The Guardian", "https://www.theguardian.com/uk/business/rss"),
        ("Sky News", "https://feeds.skynews.com/feeds/rss/business.xml"),
    ],
    "science": [
        ("BBC News", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
        ("The Guardian", "https://www.theguardian.com/science/rss"),
        ("New Scientist", "https://www.newscientist.com/feed/home/"),
    ],
}

CATEGORIES = list(FEEDS)

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    domain: str
    summary: str = ""
    image: str | None = None
    published_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _clean_text(value: str | None, limit: int = 240) -> str:
    """Strip HTML tags/entities and collapse whitespace."""
    if not value:
        return ""
    text = _TAG_RE.sub(" ", value)
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
        .replace("&nbsp;", " ")
    )
    text = _WS_RE.sub(" ", text).strip()
    if len(text) > limit:
        text = text[: limit - 1].rsplit(" ", 1)[0] + "…"
    return text


def _parse_date(value: str | None) -> str | None:
    """RFC 822 (RSS) or ISO 8601 (Atom) -> UTC ISO string, else None."""
    if not value:
        return None
    value = value.strip()
    try:
        return parsedate_to_datetime(value).astimezone(UTC).isoformat()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC).isoformat()
    except ValueError:
        return None


def _find_image(entry: ET.Element) -> str | None:
    """Best thumbnail: media:thumbnail / media:content / enclosure / inline <img>."""
    best: tuple[int, str] | None = None
    for tag in ("thumbnail", "content"):
        # findall (not iter): only ElementPath supports the {*} namespace wildcard.
        for el in entry.findall(f".//{{*}}{tag}"):
            url = el.get("url")
            if not url or not url.startswith("http"):
                continue
            medium = el.get("medium", "")
            mime = el.get("type", "")
            if tag == "content" and not (
                medium == "image" or mime.startswith("image") or (not medium and not mime)
            ):
                continue
            try:
                width = int(el.get("width") or 0)
            except ValueError:
                width = 0
            if best is None or width > best[0]:
                best = (width, url)
    if best:
        return best[1]
    for el in entry.findall(".//{*}enclosure"):
        url = el.get("url")
        if url and (el.get("type") or "").startswith("image"):
            return url
    # Last resort: first <img src> embedded in any HTML body field
    # (Verge puts it in Atom <content>, TechCrunch in <content:encoded>).
    html_body = " ".join(
        entry.findtext(f"{{*}}{tag}") or ""
        for tag in ("description", "summary", "content", "encoded")
    )
    match = re.search(r'<img[^>]+src="(https?://[^"]+?)"', html_body)
    return html.unescape(match.group(1)) if match else None


def _entry_link(entry: ET.Element) -> str:
    """RSS <link>text</link> or Atom <link rel="alternate" href>."""
    text = (entry.findtext("{*}link") or "").strip()
    if text.startswith("http"):
        return text
    fallback = ""
    for el in entry.findall("{*}link"):
        href = (el.get("href") or "").strip()
        if not href.startswith("http"):
            continue
        if el.get("rel", "alternate") == "alternate":
            return href
        fallback = fallback or href
    return fallback


def parse_feed(xml_text: str, source: str) -> list[NewsItem]:
    """Parse an RSS 2.0 or Atom document into NewsItems. Never raises."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        # Some feeds prepend junk (BOM, comments) — retry from the first tag.
        start = xml_text.find("<")
        if start <= 0:
            return []
        try:
            root = ET.fromstring(xml_text[start:])
        except ET.ParseError:
            return []

    entries = root.findall(".//{*}item") or root.findall(".//{*}entry")
    items = [_parse_entry(entry, source) for entry in entries]

    return [i for i in items if i.title and i.url][:_PER_FEED]


def _parse_entry(entry: ET.Element, source: str) -> NewsItem:
    url = _entry_link(entry)
    summary = entry.findtext("{*}description") or entry.findtext("{*}summary") or ""
    published = (
        entry.findtext("{*}pubDate")
        or entry.findtext("{*}published")
        or entry.findtext("{*}updated")
    )
    return NewsItem(
        title=_clean_text(entry.findtext("{*}title"), limit=200),
        url=url,
        source=source,
        domain=domain_of(url) if url else "",
        summary=_clean_text(summary),
        image=_find_image(entry),
        published_at=_parse_date(published),
    )


def interleave(groups: list[list[NewsItem]]) -> list[NewsItem]:
    """Round-robin across sources so no single publisher dominates the page."""
    out: list[NewsItem] = []
    idx = 0
    while True:
        added = False
        for group in groups:
            if idx < len(group):
                out.append(group[idx])
                added = True
        if not added:
            return out
        idx += 1


def _dedupe(items: list[NewsItem]) -> list[NewsItem]:
    seen: set[str] = set()
    out: list[NewsItem] = []
    for item in items:
        key = item.url.split("?")[0].rstrip("/") or item.title.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


async def _fetch_feed(client: httpx.AsyncClient, source: str, url: str) -> list[NewsItem]:
    try:
        resp = await client.get(url, headers=default_headers())
        resp.raise_for_status()
        items = parse_feed(resp.text, source)
        # Feeds are newest-first already; sort defensively when dates exist.
        items.sort(key=lambda i: i.published_at or "", reverse=True)
        return items
    except Exception as exc:  # noqa: BLE001 - one dead feed must not kill the page
        log.warning("news feed failed %s: %s", url, exc)
        return []


async def get_news(category: str, limit: int = 24) -> list[dict]:
    """Aggregated, deduped, source-interleaved news for a category (cached)."""
    category = category if category in FEEDS else "top"
    cache_key = make_key("news", category)
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached[:limit]

    async with httpx.AsyncClient(follow_redirects=True, timeout=_TIMEOUT) as client:
        groups = await asyncio.gather(
            *(_fetch_feed(client, source, url) for source, url in FEEDS[category])
        )

    items = [i.to_dict() for i in _dedupe(interleave(list(groups)))]
    if items:
        await cache.set(cache_key, items, ttl=_CACHE_TTL)
    return items[:limit]
