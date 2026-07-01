"""Research orchestration: understand → search → read → rank → answer → verify."""

from __future__ import annotations

import asyncio
import re
import time
from datetime import UTC, datetime

from app.cache import cache
from app.cache.manager import make_key
from app.config import settings
from app.fetch import fetch_many
from app.llm import llm
from app.llm.client import LLMError
from app.logging import get_logger
from app.models import (
    ConversationTurn,
    ModelInfo,
    ProgressEvent,
    ProgressStage,
    ResearchMode,
    ResearchResult,
    ResearchTimings,
    Source,
)
from app.research.answer import generate_answer
from app.research.dedupe import dedupe_pages, dedupe_search_results
from app.research.modes import get_mode
from app.research.rank import rank_pages
from app.research.session import ResearchSession
from app.search import multi_search

log = get_logger("research")


def _fast_model() -> str:
    """Default model for small utility calls (routing, query rewriting)."""
    from app.llm.personas import chat_model, get_persona

    return chat_model(get_persona(None))


# --------------------------------------------------------------------------- #
#  Chat fast path: plain conversation skips search/fetch/rank entirely
# --------------------------------------------------------------------------- #
# ponytail: regex pre-filter + one-word LLM router; add embeddings if it misroutes
_SEARCH_RE = re.compile(
    r"\b(search|research|find|look ?up|latest|news|today|current|recent|update[sd]?|"
    r"price|weather|stock|score|release[sd]?|announce[sd]?|20\d\d|vs\.?|versus|"
    r"who (won|is the)|what happened)\b",
    re.I,
)
_CHAT_RE = re.compile(
    r"^(hi|hello|hey|yo|sup|thanks?( you)?|thank you|ok(ay)?|cool|nice|lol|"
    r"good (morning|afternoon|evening|night)|how are you|who are you|what are you|"
    r"what can you do|help)\b",
    re.I,
)


async def _needs_search(query: str, context: list[ConversationTurn]) -> bool:
    q = query.strip()
    if _SEARCH_RE.search(q):
        return True
    if _CHAT_RE.match(q) and len(q) <= 80:
        return False
    if not llm.available():
        return True  # extractive fallback needs sources
    prompt = (
        "Classify the user message. Reply with exactly one word.\n"
        "SEARCH — needs live web sources (facts about the world, products, events, "
        "docs, anything that benefits from citations).\n"
        "CHAT — greeting, small talk, opinion, writing/coding help, math, or general "
        "knowledge you can answer well without searching.\n\n"
        f'Message: "{q[:500]}"'
    )
    try:
        res = await llm.chat(
            [{"role": "user", "content": prompt}], model=_fast_model(), temperature=0.0
        )
    except LLMError:
        return True
    return not res.content.strip().upper().startswith("CHAT")


async def _run_chat(session: ResearchSession, started: float) -> ResearchResult:
    """Answer conversationally with the persona's model. No search, no citations."""
    from app.llm.personas import chat_model, chat_system, get_persona
    from app.research.answer import _stream_or_chat

    persona = get_persona(session.persona)

    # Signal the UI to switch to the chat (Thinking…) view, not the search trail.
    session.emit(
        ProgressEvent(
            stage=ProgressStage.writing, status="active", message="Thinking",
            progress=0.2, data={"chat": True},
        )
    )

    async def on_delta(text: str) -> None:
        session.emit(
            ProgressEvent(
                stage=ProgressStage.writing, status="active", message="",
                progress=0.7, data={"delta": text},
            )
        )

    messages: list[dict] = []
    for turn in session.context[-6:]:
        messages.append({"role": "user", "content": turn.query})
        if turn.answer:
            messages.append({"role": "assistant", "content": turn.answer})
    messages.append({"role": "user", "content": session.query})

    grounded = llm.available()
    if grounded:
        try:
            text = await _stream_or_chat(
                messages, chat_model(persona), chat_system(persona), on_delta, temperature=0.6
            )
        except LLMError as exc:
            log.warning("chat answer failed: %s", exc)
            text, grounded = "", False
    else:
        text = ""
    if not text.strip():
        text = (
            "No language model is configured, so I can't chat directly. "
            "Try a research query instead — search and extraction still work."
        )

    from app.models import Answer

    total_ms = int((time.monotonic() - started) * 1000)
    result = ResearchResult(
        id=session.id,
        query=session.query,
        mode=session.mode,
        persona=session.persona,
        status="complete",
        answer=Answer(detail=text, confidence=0.9 if grounded else 0.0),
        sources=[],
        confidence=0.9 if grounded else 0.0,
        model=ModelInfo(model=persona.name, available=llm.available(), grounded=grounded),
        timings=ResearchTimings(answer_ms=total_ms, total_ms=total_ms),
        created_at=datetime.now(UTC).isoformat(),
    )
    session.emit(
        ProgressEvent(
            stage=ProgressStage.done, status="done", message="Complete", progress=1.0,
            data={"result": result.model_dump(mode="json")},
        )
    )
    session.finish(result)
    return result


async def _standalone_query(query: str, context: list[ConversationTurn]) -> str:
    """Turn a context-dependent follow-up (“why is that?”) into a self-contained query."""
    if not context:
        return query
    heuristic = f"{context[-1].query} {query}".strip()
    if not llm.available():
        return heuristic
    convo = "\n".join(f"Q: {t.query}" for t in context[-4:])
    prompt = (
        f"Conversation so far:\n{convo}\n\n"
        f"Rewrite this follow-up into ONE standalone web search query that makes sense "
        f"without the conversation. Return only the query.\nFollow-up: {query}"
    )
    try:
        res = await llm.chat(
            [{"role": "user", "content": prompt}], model=_fast_model(), temperature=0.2
        )
    except LLMError:
        return heuristic
    line = next((ln.strip("-*• \t\"") for ln in res.content.splitlines() if ln.strip()), "")
    return line if 3 <= len(line) <= 200 else heuristic


async def _expand_query(query: str, n: int) -> list[str]:
    """Ask the model for alternative sub-queries (best-effort, optional)."""
    if n <= 0 or not llm.available():
        return []
    prompt = (
        f"Generate {n} alternative web search queries that would help answer:\n"
        f'"{query}"\n\n'
        "Return ONLY the queries, one per line, no numbering, no extra text."
    )
    try:
        res = await llm.chat(
            [{"role": "user", "content": prompt}], model=_fast_model(), temperature=0.4
        )
    except LLMError:
        return []
    lines = [ln.strip("-*• \t") for ln in res.content.splitlines() if ln.strip()]
    cleaned = [ln for ln in lines if 3 <= len(ln) <= 200 and ln.lower() != query.lower()]
    return cleaned[:n]


def _cache_key(query: str, mode: ResearchMode, context: list[ConversationTurn]) -> str:
    ctx_sig = "|".join(t.query for t in context)
    return make_key("research", query.lower().strip(), mode.value, ctx_sig)


async def run_research(session: ResearchSession) -> ResearchResult:
    """Execute the full pipeline for a session, emitting progress events."""
    query, mode_enum = session.query, session.mode
    context = session.context
    mode = get_mode(mode_enum)
    started = time.monotonic()

    def emit(stage: ProgressStage, message: str, progress: float, **data) -> None:
        session.emit(
            ProgressEvent(stage=stage, status="active", message=message, progress=progress, data=data)
        )

    # --- Short-circuit on cached result ---
    cached = await cache.get(_cache_key(query, mode_enum, context))
    if cached is not None:
        result = ResearchResult(**cached)
        result.id = session.id
        emit(ProgressStage.understanding, "Loaded from cache", 0.5, cached=True)
        session.emit(
            ProgressEvent(
                stage=ProgressStage.done, status="done", message="Complete (cached)",
                progress=1.0, data={"result": result.model_dump(mode="json")},
            )
        )
        session.finish(result)
        return result

    try:
        # --- 0. Route + seed search, concurrently ---
        # The chat/search router runs in parallel with the optimistic seed
        # search chain, so research queries pay zero routing latency and chat
        # queries only wait for the (fast) router. No research-stage events are
        # emitted for chat — the UI shows a Thinking indicator instead.
        t_search = time.monotonic()

        async def _seed_chain() -> tuple[str, list]:
            seed = await _standalone_query(query, context)
            return seed, await multi_search(
                [seed], providers=settings.search_providers, limit=mode.search_limit
            )

        route_task = asyncio.create_task(_needs_search(query, context))
        seed_task = asyncio.create_task(_seed_chain())
        if not await route_task:
            seed_task.cancel()
            return await _run_chat(session, started)

        # --- 1. Understanding ---
        emit(ProgressStage.understanding, "Understanding your question", 0.05)
        extra = await _expand_query(query, mode.expansions)
        if extra:
            emit(ProgressStage.understanding, "Expanded the query", 0.1, subqueries=extra)

        # --- 2. Searching ---
        emit(ProgressStage.searching, "Searching the web", 0.2)
        extra_results = (
            await multi_search(extra, providers=settings.search_providers, limit=mode.search_limit)
            if extra
            else []
        )
        search_seed, seed_results = await seed_task
        raw_results = seed_results + extra_results
        search_ms = int((time.monotonic() - t_search) * 1000)

        # --- 3. Finding sources (dedupe search hits) ---
        results = dedupe_search_results(raw_results)
        emit(
            ProgressStage.finding_sources,
            f"Found {len(results)} candidate sources",
            0.35,
            candidates=len(results),
            providers=settings.search_providers,
        )
        if not results:
            return await _finalize_empty(session, mode_enum, started, search_ms)

        # --- 4. Reading pages ---
        to_fetch = [r.url for r in results[: mode.max_fetch]]
        emit(ProgressStage.reading, f"Reading {len(to_fetch)} pages", 0.5, reading=len(to_fetch))
        t_fetch = time.monotonic()
        pages = await fetch_many(to_fetch, max_chars=settings.fetch_max_chars)
        fetch_ms = int((time.monotonic() - t_fetch) * 1000)
        readable = [p for p in pages if p.ok and p.text]
        emit(
            ProgressStage.reading,
            f"Extracted content from {len(readable)} pages",
            0.6,
            readable=len(readable),
        )
        if not readable:
            return await _finalize_empty(session, mode_enum, started, search_ms, fetch_ms)

        # --- 5. Deduping content ---
        emit(ProgressStage.deduping, "Removing duplicate content", 0.7)
        unique = dedupe_pages(readable)

        # --- 6. Ranking ---
        emit(ProgressStage.ranking, "Ranking evidence by relevance", 0.8)
        sources: list[Source] = rank_pages(search_seed, unique, mode)
        session.emit(
            ProgressEvent(
                stage=ProgressStage.ranking, status="done", message="Ranked sources",
                progress=0.82,
                data={"sources": [s.model_dump(mode="json") for s in sources]},
            )
        )

        # --- 7. Writing the answer (streamed) ---
        emit(ProgressStage.writing, "Writing a grounded answer", 0.85)

        async def on_delta(text: str) -> None:
            session.emit(
                ProgressEvent(
                    stage=ProgressStage.writing, status="active", message="",
                    progress=0.9, data={"delta": text},
                )
            )

        t_answer = time.monotonic()
        answer, model_info, sources = await generate_answer(
            query, mode, sources, on_delta, context=context, persona_key=session.persona
        )
        answer_ms = int((time.monotonic() - t_answer) * 1000)

        # --- 8. Verifying citations ---
        emit(
            ProgressStage.verifying,
            "Checking citations against sources",
            0.98,
            used=answer.citations,
        )

        total_ms = int((time.monotonic() - started) * 1000)
        result = ResearchResult(
            id=session.id,
            query=query,
            mode=mode_enum,
            persona=session.persona,
            status="complete",
            answer=answer,
            sources=sources,
            confidence=answer.confidence,
            model=model_info,
            timings=ResearchTimings(
                search_ms=search_ms, fetch_ms=fetch_ms, answer_ms=answer_ms, total_ms=total_ms
            ),
            created_at=datetime.now(UTC).isoformat(),
        )
        await cache.set(
            _cache_key(query, mode_enum, context), result.model_dump(mode="json"),
            ttl=settings.cache_ttl_research,
        )
        session.emit(
            ProgressEvent(
                stage=ProgressStage.done, status="done", message="Complete", progress=1.0,
                data={"result": result.model_dump(mode="json")},
            )
        )
        session.finish(result)
        log.info("research done: '%s' (%s) in %dms", query[:60], mode_enum.value, total_ms)
        return result

    except Exception as exc:  # pragma: no cover - top-level safety net
        log.exception("research failed: %s", exc)
        result = ResearchResult(
            id=session.id, query=query, mode=mode_enum, persona=session.persona, status="error",
            error=str(exc), created_at=datetime.now(UTC).isoformat(),
        )
        session.emit(
            ProgressEvent(
                stage=ProgressStage.error, status="error", message=str(exc), progress=1.0,
                data={"result": result.model_dump(mode="json")},
            )
        )
        session.finish(result)
        return result


async def _finalize_empty(
    session: ResearchSession,
    mode_enum: ResearchMode,
    started: float,
    search_ms: int,
    fetch_ms: int = 0,
) -> ResearchResult:
    from app.llm import get_persona
    from app.research.answer import _no_sources_answer

    answer = _no_sources_answer(session.query)
    persona = get_persona(session.persona)
    total_ms = int((time.monotonic() - started) * 1000)
    result = ResearchResult(
        id=session.id, query=session.query, mode=mode_enum, persona=session.persona,
        status="complete", answer=answer, sources=[], confidence=0.0,
        model=ModelInfo(model=persona.name, available=llm.available(), grounded=False),
        timings=ResearchTimings(search_ms=search_ms, fetch_ms=fetch_ms, total_ms=total_ms),
        created_at=datetime.now(UTC).isoformat(),
    )
    session.emit(
        ProgressEvent(
            stage=ProgressStage.done, status="done", message="No sources found",
            progress=1.0, data={"result": result.model_dump(mode="json")},
        )
    )
    session.finish(result)
    return result
