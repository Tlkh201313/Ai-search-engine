"""Grounded answer synthesis with an LLM, plus a deterministic fallback."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

from app.llm import llm
from app.llm.client import LLMError
from app.logging import get_logger
from app.models import Answer, ModelInfo, Source
from app.research.citations import apply_citations, sanitize
from app.research.modes import ModeConfig
from app.textutil import truncate_words

log = get_logger("answer")

DeltaCallback = Callable[[str], Awaitable[None]]

_SYSTEM = """You are a rigorous research assistant. You answer questions using ONLY the numbered sources provided by the user. Follow every rule:

1. Ground every factual claim in the sources and cite with bracketed numbers like [1] or [2][3].
2. Never invent facts, URLs, dates, authors, or citations. Never cite a source number that was not provided.
3. If the sources are weak, incomplete, or conflicting, say so plainly.
4. Prefer specific, verifiable statements over vague ones.
5. Write in a calm, clear, trustworthy voice. No hype, no filler.

Respond in EXACTLY this markdown template (keep the headers verbatim):

## Answer
A direct 1-3 sentence answer with citations.

## Details
A well-structured explanation in markdown. Cite claims inline with [n].

## Key Takeaways
- concise point with citation [n]
- concise point with citation [n]

## Agreements
- where multiple sources agree [n][m]  (write "None" if not applicable)

## Disagreements
- where sources conflict, attributed [n] vs [m]  (write "None" if not applicable)

## Uncertainties
- what is missing, unverified, or out of date  (write "None" if not applicable)

## Follow-ups
- a natural next question
- a natural next question
"""

_HEADER_MAP = {
    "answer": "summary",
    "details": "detail",
    "detail": "detail",
    "key takeaways": "key_takeaways",
    "takeaways": "key_takeaways",
    "agreements": "agreements",
    "disagreements": "disagreements",
    "uncertainties": "uncertainties",
    "follow-ups": "follow_ups",
    "follow ups": "follow_ups",
    "followups": "follow_ups",
}
_LIST_FIELDS = {"key_takeaways", "agreements", "disagreements", "uncertainties", "follow_ups"}
_HEADER_RE = re.compile(r"^#{1,6}\s+(.*)$")


def _build_user_prompt(query: str, mode: ModeConfig, sources: list[Source]) -> str:
    lines = [f"Question: {query}", "", f"Mode: {mode.label} — {mode.style}", "", "Sources:"]
    for s in sources:
        meta = s.domain
        if s.published_at:
            meta += f" · {s.published_at[:10]}"
        lines.append(f"\n[{s.id}] {s.title} ({meta})")
        lines.append(s.excerpt or s.snippet)
    lines.append(
        "\nWrite the answer now using only these sources and the required template."
    )
    return "\n".join(lines)


def _parse_sections(text: str) -> dict[str, object]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        header = _HEADER_RE.match(raw.strip())
        if header:
            name = header.group(1).strip().lower().rstrip(":")
            current = _HEADER_MAP.get(name)
            if current is not None:
                sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(raw)

    result: dict[str, object] = {}
    for key, lines in sections.items():
        if key in _LIST_FIELDS:
            items = []
            for ln in lines:
                stripped = ln.strip().lstrip("-*• ").strip()
                if not stripped:
                    continue
                if stripped.lower() in {"none", "n/a", "none.", "not applicable"}:
                    continue
                items.append(stripped)
            result[key] = items
        else:
            result[key] = "\n".join(lines).strip()
    return result


def _compute_confidence(sources: list[Source], used: list[int], grounded: bool) -> float:
    if not sources:
        return 0.0
    used_sources = [s for s in sources if s.id in set(used)] or sources[:3]
    avg_quality = sum(s.scores.overall for s in used_sources) / len(used_sources)
    coverage = min(1.0, len(used_sources) / 3.0)
    base = 0.5 * avg_quality + 0.3 * coverage + (0.2 if grounded else 0.05)
    return round(min(0.97, base), 2)


async def generate_answer(
    query: str,
    mode: ModeConfig,
    sources: list[Source],
    on_delta: DeltaCallback | None = None,
) -> tuple[Answer, ModelInfo]:
    """Produce a grounded Answer. Streams deltas via ``on_delta`` when possible."""
    if not sources:
        return _no_sources_answer(query), ModelInfo(
            model=llm.model, available=llm.available(), grounded=False
        )

    if llm.available():
        try:
            return await _llm_answer(query, mode, sources, on_delta)
        except LLMError as exc:
            log.warning("LLM answer failed, using extractive fallback: %s", exc)

    answer = _extractive_answer(query, mode, sources)
    if on_delta:
        await on_delta(answer.detail)
    return answer, ModelInfo(model=llm.model, available=llm.available(), grounded=False)


async def _llm_answer(
    query: str,
    mode: ModeConfig,
    sources: list[Source],
    on_delta: DeltaCallback | None,
) -> tuple[Answer, ModelInfo]:
    user_prompt = _build_user_prompt(query, mode, sources)
    chunks: list[str] = []
    async for delta in llm.stream(
        [{"role": "user", "content": user_prompt}], system=_SYSTEM, temperature=0.2
    ):
        chunks.append(delta)
        if on_delta:
            await on_delta(delta)
    full = "".join(chunks).strip()
    parsed = _parse_sections(full)

    valid_ids = {s.id for s in sources}
    summary = sanitize(str(parsed.get("summary", "")), valid_ids)
    detail = sanitize(str(parsed.get("detail", "")) or full, valid_ids)
    takeaways = [sanitize(t, valid_ids) for t in parsed.get("key_takeaways", [])]  # type: ignore
    agreements = [sanitize(t, valid_ids) for t in parsed.get("agreements", [])]  # type: ignore
    disagreements = [sanitize(t, valid_ids) for t in parsed.get("disagreements", [])]  # type: ignore
    uncertainties = list(parsed.get("uncertainties", []))  # type: ignore
    follow_ups = list(parsed.get("follow_ups", []))  # type: ignore

    used = apply_citations([summary, detail, *takeaways, *agreements, *disagreements], sources)
    confidence = _compute_confidence(sources, used, grounded=True)

    answer = Answer(
        summary=summary or truncate_words(detail, 40),
        detail=detail,
        key_takeaways=takeaways,
        agreements=agreements,
        disagreements=disagreements,
        uncertainties=uncertainties,
        follow_ups=follow_ups[:4],
        citations=used,
        confidence=confidence,
    )
    return answer, ModelInfo(model=llm.model, available=True, grounded=True)


def _extractive_answer(query: str, mode: ModeConfig, sources: list[Source]) -> Answer:
    """Deterministic, source-grounded answer when no LLM is configured."""
    top = sources[: min(5, len(sources))]
    detail_lines = [
        "_No language model is configured, so this is a direct extract from the "
        "top-ranked sources rather than a synthesized answer._\n"
    ]
    takeaways = []
    for s in top:
        evidence = truncate_words((s.snippet or s.excerpt).replace("\n", " "), 45)
        detail_lines.append(f"- **{s.domain}** — {evidence} [{s.id}]")
        takeaways.append(f"{truncate_words(s.title, 14)} [{s.id}]")
    detail = "\n".join(detail_lines)
    used = apply_citations([detail], sources)
    return Answer(
        summary=(
            f"Found {len(sources)} relevant source(s) for “{truncate_words(query, 20)}”. "
            "Key evidence is summarized below; configure a model for a synthesized answer."
        ),
        detail=detail,
        key_takeaways=takeaways[:5],
        uncertainties=["No model was available to cross-check or synthesize these sources."],
        follow_ups=[f"What do the most recent sources say about {truncate_words(query, 10)}?"],
        citations=used,
        confidence=_compute_confidence(sources, used, grounded=False),
    )


def _no_sources_answer(query: str) -> Answer:
    return Answer(
        summary="No sources could be retrieved for this query.",
        detail=(
            "The search step returned no readable sources. This can happen when the "
            "query is very niche, a search provider is rate-limited, or network access "
            "is restricted. Try rephrasing, or enable another search provider."
        ),
        uncertainties=["The answer is unverified because no sources were found."],
        follow_ups=[f"Try a broader phrasing of: {truncate_words(query, 12)}"],
        confidence=0.0,
    )
