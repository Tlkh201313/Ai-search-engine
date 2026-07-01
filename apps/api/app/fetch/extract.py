"""Extract clean readable text + metadata from HTML.

Uses trafilatura when installed (best-in-class boilerplate removal) and falls
back to a selectolax-based extractor so the app works without it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from selectolax.parser import HTMLParser

try:  # optional, high-quality extractor
    import trafilatura

    _HAS_TRAFILATURA = True
except Exception:  # pragma: no cover
    _HAS_TRAFILATURA = False

_STRIP = ("script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg")
_WS = re.compile(r"[ \t]+")
_MULTINL = re.compile(r"\n{3,}")


@dataclass
class Extracted:
    title: str = ""
    text: str = ""
    author: str | None = None
    description: str | None = None
    published_at: str | None = None
    canonical: str | None = None
    meta: dict[str, str] = field(default_factory=dict)


def extract(html: str, url: str, max_chars: int) -> Extracted:
    meta = _read_meta(html)
    text = ""
    if _HAS_TRAFILATURA:
        text = (
            trafilatura.extract(
                html, include_comments=False, include_tables=True, favor_precision=True
            )
            or ""
        )
    if not text:
        text = _fallback_text(html)
    text = _clean(text)[:max_chars]
    if _HAS_TRAFILATURA:
        _enrich_meta(html, meta)
    return Extracted(
        title=meta.get("title", ""),
        text=text,
        author=meta.get("author"),
        description=meta.get("description"),
        published_at=meta.get("published_at"),
        canonical=meta.get("canonical"),
        meta=meta,
    )


def _enrich_meta(html: str, meta: dict[str, str]) -> None:
    """Fill only the metadata fields the HTML tags didn't already provide."""
    try:
        doc = trafilatura.extract_metadata(html)
    except Exception:
        return
    if doc is None:
        return
    for key, value in (
        ("title", getattr(doc, "title", None)),
        ("author", getattr(doc, "author", None)),
        ("published_at", getattr(doc, "date", None)),
        ("description", getattr(doc, "description", None)),
    ):
        if not meta.get(key) and value:
            meta[key] = str(value)


def _read_meta(html: str) -> dict[str, str]:
    tree = HTMLParser(html)
    out: dict[str, str] = {}

    def _meta(*selectors: str) -> str | None:
        for sel in selectors:
            node = tree.css_first(sel)
            if node is not None:
                content = node.attributes.get("content")
                if content:
                    return content.strip()
        return None

    title = _meta('meta[property="og:title"]', 'meta[name="twitter:title"]')
    if not title:
        t = tree.css_first("title")
        title = t.text(strip=True) if t else ""
    out["title"] = title or ""

    if desc := _meta(
        'meta[property="og:description"]', 'meta[name="description"]',
        'meta[name="twitter:description"]',
    ):
        out["description"] = desc
    if author := _meta('meta[name="author"]', 'meta[property="article:author"]'):
        out["author"] = author
    if published := _meta(
        'meta[property="article:published_time"]',
        'meta[property="og:published_time"]',
        'meta[name="date"]',
        'meta[itemprop="datePublished"]',
    ):
        out["published_at"] = published
    else:
        time_node = tree.css_first("time[datetime]")
        if time_node is not None:
            dt = time_node.attributes.get("datetime")
            if dt:
                out["published_at"] = dt.strip()

    canonical = tree.css_first('link[rel="canonical"]')
    if canonical is not None:
        href = canonical.attributes.get("href")
        if href:
            out["canonical"] = href.strip()
    return out


def _fallback_text(html: str) -> str:
    tree = HTMLParser(html)
    for tag in _STRIP:
        for node in tree.css(tag):
            node.decompose()
    main = tree.css_first("article") or tree.css_first("main") or tree.body
    if main is None:
        return ""
    return main.text(separator="\n", strip=True)


def _clean(text: str) -> str:
    lines = [_WS.sub(" ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    joined = "\n".join(lines)
    return _MULTINL.sub("\n\n", joined).strip()
