"""Tools the models can call during research, plus a citable-source collector.

Exposed to the model as OpenAI function tools:
- web_search(query): discover candidate sources (titles/urls/snippets only)
- read_url(url):     fetch + read a page; it becomes a numbered, citable source
"""

from __future__ import annotations

import json

from app.fetch import fetch_page
from app.logging import get_logger
from app.models import Source, SourceScores
from app.research.rank import build_excerpt
from app.search import multi_search
from app.textutil import domain_of, jaccard, keywords, normalize_url

log = get_logger("tools")

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for candidate sources. Returns titles, URLs, and short "
                "snippets only (not full page text). Use focused queries; call read_url to "
                "actually read a promising result."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "the search query"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_url",
            "description": (
                "Fetch and read the clean text of a web page. The page becomes a numbered "
                "source that you must cite by the returned id. Prefer primary sources."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "absolute http(s) URL to read"}
                },
                "required": ["url"],
            },
        },
    },
]


class SourceCollector:
    """Holds the current sources and mints new, deduped, citable ones."""

    def __init__(self, sources: list[Source], query: str) -> None:
        self.query = query
        self.sources: list[Source] = list(sources)
        self._seen: dict[str, Source] = {normalize_url(s.url): s for s in sources}
        self._next_id = max((s.id for s in sources), default=0) + 1
        self.tool_reads = 0

    def add_page(self, page) -> Source:
        norm = normalize_url(page.url)
        if norm in self._seen:
            return self._seen[norm]
        query_kw = keywords(self.query)
        relevance = round(jaccard(query_kw, keywords(page.text[:4000])), 4) if query_kw else 0.5
        source = Source(
            id=self._next_id,
            url=page.url,
            title=page.title or page.domain,
            domain=page.domain or domain_of(page.url),
            snippet=(page.description or page.text[:280]).strip(),
            excerpt=build_excerpt(self.query, page.text),
            author=page.author,
            description=page.description,
            published_at=page.published_at,
            fetched_at=page.fetched_at,
            favicon=f"https://www.google.com/s2/favicons?domain={page.domain}&sz=64",
            provider="tool",
            word_count=page.word_count,
            scores=SourceScores(relevance=relevance, quality=0.6, depth=0.5, overall=0.6),
        )
        self._next_id += 1
        self._seen[norm] = source
        self.sources.append(source)
        return source


async def execute_tool(name: str, arguments: dict, collector: SourceCollector) -> str:
    """Run a tool call and return a JSON string for the model."""
    try:
        if name == "web_search":
            query = str(arguments.get("query", "")).strip()
            if not query:
                return json.dumps({"error": "missing query"})
            results = await multi_search([query], limit=6)
            return json.dumps(
                {
                    "results": [
                        {"title": r.title, "url": r.url, "snippet": r.snippet[:240]}
                        for r in results[:6]
                    ]
                }
            )
        if name == "read_url":
            url = str(arguments.get("url", "")).strip()
            if not url:
                return json.dumps({"error": "missing url"})
            collector.tool_reads += 1
            page = await fetch_page(url)
            if not page.ok:
                return json.dumps({"error": page.error or "could not read page", "url": url})
            source = collector.add_page(page)
            return json.dumps(
                {
                    "id": source.id,
                    "title": source.title,
                    "domain": source.domain,
                    "published_at": source.published_at,
                    "excerpt": source.excerpt,
                    "note": f"Cite this source as [{source.id}].",
                }
            )
        return json.dumps({"error": f"unknown tool: {name}"})
    except Exception as exc:  # pragma: no cover - tools never crash the loop
        log.warning("tool %s failed: %s", name, exc)
        return json.dumps({"error": str(exc)})
