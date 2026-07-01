"""Small, dependency-free text and URL helpers shared across the pipeline."""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

_TRACKING_PREFIXES = ("utm_", "mc_", "pk_")
_TRACKING_KEYS = {"fbclid", "gclid", "ref", "ref_src", "igshid", "spm", "_hsenc"}
_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "was", "were", "be", "with", "as", "by", "at", "that", "this", "it", "from",
    "what", "how", "why", "when", "which", "who", "does", "do", "can", "will",
}


def normalize_url(url: str) -> str:
    """Canonicalize a URL for dedup: drop scheme/host case, www, tracking, fragment."""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return url.strip().lower()
    scheme = "https"
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/") or "/"
    kept = []
    for pair in parsed.query.split("&"):
        if not pair:
            continue
        key = pair.split("=", 1)[0]
        low = key.lower()
        if low in _TRACKING_KEYS or any(low.startswith(p) for p in _TRACKING_PREFIXES):
            continue
        kept.append(pair)
    query = "&".join(sorted(kept))
    return urlunparse((scheme, netloc, path, "", query, ""))


def domain_of(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
    except ValueError:
        return ""
    return netloc[4:] if netloc.startswith("www.") else netloc


def tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def keywords(text: str) -> set[str]:
    return {t for t in tokenize(text) if t not in _STOPWORDS and len(t) > 1}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def title_similarity(a: str, b: str) -> float:
    from difflib import SequenceMatcher

    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + " …"
