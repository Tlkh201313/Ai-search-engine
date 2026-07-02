"""Parse, validate, and map inline [n] citations to real sources.

Rules enforced here:
- Never keep a citation to a source that does not exist (out of range).
- Only sources actually referenced are marked ``used``.
"""

from __future__ import annotations

import re

from app.models import Source

_CITE_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


def extract_ids(text: str) -> list[int]:
    ids: list[int] = []
    for group in _CITE_RE.findall(text):
        for part in group.split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(int(part))
    return ids


def sanitize(text: str, valid_ids: set[int]) -> str:
    """Remove citation markers that reference non-existent sources."""

    def _replace(match: re.Match) -> str:
        parts = [p.strip() for p in match.group(1).split(",")]
        kept = [p for p in parts if p.isdigit() and int(p) in valid_ids]
        if not kept:
            return ""
        return "[" + "][".join(kept) + "]"

    return _CITE_RE.sub(_replace, text)


def apply_citations(texts: list[str], sources: list[Source]) -> list[int]:
    """Validate citations across answer texts; mark used sources; return used ids.

    ``texts`` are mutated in place is not possible (strings immutable); callers
    should use :func:`sanitize` on individual fields. This returns the ordered
    list of unique, valid source ids referenced anywhere in ``texts``.
    """
    valid = {s.id for s in sources}
    used: list[int] = []
    for text in texts:
        for cid in extract_ids(text):
            if cid in valid and cid not in used:
                used.append(cid)
    used_set = set(used)
    for source in sources:
        source.used = source.id in used_set
    return sorted(used)
