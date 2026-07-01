"""Answer synthesis: persona-driven, tool-using, with a deterministic fallback.

Each research persona (see app/llm/personas.py) writes the answer using its own
system prompt and may call in-app tools (web_search, read_url) to gather more
evidence. Zephyr is a two-model fusion (plan → execute → check). When no model
is configured, a deterministic extractive answer is returned instead.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

from app.config import settings
from app.llm import Persona, get_persona, llm
from app.llm.client import LLMError
from app.llm.tools import TOOL_SCHEMAS, SourceCollector, execute_tool
from app.logging import get_logger
from app.models import Answer, ConversationTurn, ModelInfo, Source
from app.research.citations import apply_citations, sanitize
from app.research.modes import ModeConfig
from app.textutil import truncate_words

log = get_logger("answer")

DeltaCallback = Callable[[str], Awaitable[None]]

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


# --------------------------------------------------------------------------- #
#  Public entry point
# --------------------------------------------------------------------------- #
async def generate_answer(
    query: str,
    mode: ModeConfig,
    sources: list[Source],
    on_delta: DeltaCallback | None = None,
    context: list[ConversationTurn] | None = None,
    persona_key: str | None = None,
) -> tuple[Answer, ModelInfo, list[Source]]:
    """Produce a grounded Answer. Returns (answer, model_info, final_sources)."""
    context = context or []
    persona = get_persona(persona_key)

    if not sources:
        return (
            _no_sources_answer(query),
            ModelInfo(model=persona.name, available=llm.available(), grounded=False),
            [],
        )

    if llm.available():
        try:
            if persona.fusion:
                final_text, collector = await _fusion_answer(
                    query, mode, sources, context, persona, on_delta
                )
            else:
                collector = SourceCollector(sources, query)
                draft = await _gather(
                    query, mode, collector, context, persona.model or "", persona.system_prompt
                )
                final_text = await _synthesize(
                    query, mode, collector, context, persona.model or "",
                    persona.system_prompt, draft, on_delta,
                )
            answer, info = _finalize(final_text, collector, persona)
            return answer, info, collector.sources
        except LLMError as exc:
            log.warning("persona '%s' failed, using extractive fallback: %s", persona.key, exc)

    answer = _extractive_answer(query, sources)
    if on_delta:
        await on_delta(answer.detail)
    return answer, ModelInfo(model=persona.name, available=llm.available(), grounded=False), sources


# --------------------------------------------------------------------------- #
#  Agentic tool loop (evidence gathering, single model, no streaming)
# --------------------------------------------------------------------------- #
async def _gather(
    query: str,
    mode: ModeConfig,
    collector: SourceCollector,
    context: list[ConversationTurn],
    model: str,
    system: str,
    extra_system: str = "",
) -> str:
    """Let the model read the given sources and call tools to fill gaps.

    Returns the model's draft answer if it produced one before the tool budget
    ran out (used as notes for the streamed synthesis); otherwise ``""``.
    """
    rounds = settings.llm_max_tool_rounds if mode.tool_rounds is None else mode.tool_rounds
    if rounds <= 0:
        return ""  # mode opts out of the tool loop — synthesize straight from sources

    full_system = system if not extra_system else f"{system}\n\n{extra_system}"
    messages: list[dict] = [
        {"role": "user", "content": _build_user_prompt(query, mode, collector.sources, context)}
    ]
    tools = TOOL_SCHEMAS

    for _ in range(rounds):
        res = await llm.chat(messages, model=model, system=full_system, tools=tools, temperature=0.2)
        if not res.tool_calls:
            return res.content  # model is done gathering; keep its draft as notes
        messages.append(
            {"role": "assistant", "content": res.content or "", "tool_calls": [tc.raw for tc in res.tool_calls]}
        )
        for call in res.tool_calls:
            output = await execute_tool(call.name, call.arguments, collector)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": output})

    return ""  # budget exhausted without a draft — synthesize straight from sources


_SYNTH_INSTRUCTION = (
    "Do not call any tools now. Using only the numbered sources above (every source "
    "you read is listed), write the final answer in the required markdown template. "
    "Cite every non-obvious claim inline with [n] using only ids that exist above."
)


async def _synthesize(
    query: str,
    mode: ModeConfig,
    collector: SourceCollector,
    context: list[ConversationTurn],
    model: str,
    system: str,
    draft: str,
    on_delta: DeltaCallback | None,
) -> str:
    """Stream the final, tool-free synthesis over all collected sources."""
    lines = [_build_user_prompt(query, mode, collector.sources, context), ""]
    if draft.strip():
        lines += ["Your working draft / notes (revise and finalize):", draft, ""]
    lines.append(_SYNTH_INSTRUCTION)
    messages = [{"role": "user", "content": "\n".join(lines)}]
    return await _stream_or_chat(messages, model, system, on_delta, temperature=0.2)


# --------------------------------------------------------------------------- #
#  Streaming helper
# --------------------------------------------------------------------------- #
async def _stream_or_chat(
    messages: list[dict],
    model: str,
    system: str,
    on_delta: DeltaCallback | None,
    temperature: float = 0.2,
) -> str:
    """Stream a completion to ``on_delta`` and return the full text.

    Falls back to a single non-streaming call if streaming is unavailable or
    yields nothing, so the answer is never lost.
    """
    if on_delta is None:
        res = await llm.chat(messages, model=model, system=system, temperature=temperature)
        return res.content

    chunks: list[str] = []
    try:
        async for piece in llm.stream(messages, model=model, system=system, temperature=temperature):
            chunks.append(piece)
            await on_delta(piece)
    except LLMError as exc:
        log.info("stream failed, falling back to non-stream: %s", exc)

    text = "".join(chunks)
    if text.strip():
        return text

    res = await llm.chat(messages, model=model, system=system, temperature=temperature)
    if res.content:
        await on_delta(res.content)
    return res.content


# --------------------------------------------------------------------------- #
#  Zephyr fusion: plan (haiku) → execute (llama, tools) → check/stream (haiku)
# --------------------------------------------------------------------------- #
async def _fusion_answer(
    query: str,
    mode: ModeConfig,
    sources: list[Source],
    context: list[ConversationTurn],
    persona: Persona,
    on_delta: DeltaCallback | None = None,
) -> tuple[str, SourceCollector]:
    assert persona.fusion and persona.fusion_prompts
    executor_model, planner_model = persona.fusion
    planner_p, executor_p, checker_p = persona.fusion_prompts
    collector = SourceCollector(sources, query)

    # 1) PLAN (fast model, no tools) — best effort.
    plan = ""
    try:
        titles = "\n".join(f"[{s.id}] {s.title} ({s.domain})" for s in collector.sources)
        plan_res = await llm.chat(
            [{"role": "user", "content": f"Question: {query}\n\nAvailable sources:\n{titles}"}],
            model=planner_model,
            system=planner_p,
            temperature=0.3,
        )
        plan = plan_res.content.strip()
    except LLMError as exc:
        log.info("fusion planner skipped: %s", exc)

    # 2) EXECUTE (capable fast model, with tools) — gather evidence + a draft.
    extra = f"Research plan to follow:\n{plan}" if plan else ""
    draft = await _gather(query, mode, collector, context, executor_model, executor_p, extra)

    # 3) CHECK (fast model, no tools) — verify + fix, streamed. If the executor
    #    produced no draft, synthesize one directly instead.
    if not draft.strip():
        final = await _synthesize(
            query, mode, collector, context, executor_model, executor_p, "", on_delta
        )
        return final, collector

    numbered = "\n".join(
        f"[{s.id}] {s.title} ({s.domain})\n{s.excerpt or s.snippet}" for s in collector.sources
    )
    check_user = (
        f"Question: {query}\n\nDraft answer:\n{draft}\n\nSources:\n{numbered}\n\n"
        "Return the corrected FINAL answer in the required template."
    )
    final = await _stream_or_chat(
        [{"role": "user", "content": check_user}], planner_model, checker_p, on_delta, temperature=0.1
    )
    return (final or draft), collector


# --------------------------------------------------------------------------- #
#  Shared helpers
# --------------------------------------------------------------------------- #
def _build_user_prompt(
    query: str, mode: ModeConfig, sources: list[Source], context: list[ConversationTurn]
) -> str:
    lines: list[str] = []
    if context:
        lines.append("Conversation so far (for context; do not re-answer these):")
        for turn in context[-4:]:
            lines.append(f"Q: {turn.query}")
            if turn.answer:
                lines.append(f"A: {truncate_words(turn.answer, 60)}")
        lines.append("")
    lines += [f"Question: {query}", "", f"Mode: {mode.label} — {mode.style}", "", "Sources already retrieved:"]
    for s in sources:
        meta = s.domain
        if s.published_at:
            meta += f" · {s.published_at[:10]}"
        lines.append(f"\n[{s.id}] {s.title} ({meta})")
        lines.append(s.excerpt or s.snippet)
    lines.append(
        "\nRead these first. Use tools only to fill genuine gaps, then write the answer in the required template."
    )
    return "\n".join(lines)


def _finalize(
    final_text: str, collector: SourceCollector, persona: Persona
) -> tuple[Answer, ModelInfo]:
    parsed = _parse_sections(final_text)
    valid_ids = {s.id for s in collector.sources}

    summary = sanitize(str(parsed.get("summary", "")), valid_ids)
    detail = sanitize(str(parsed.get("detail", "")) or final_text, valid_ids)
    takeaways = [sanitize(t, valid_ids) for t in parsed.get("key_takeaways", [])]  # type: ignore
    agreements = [sanitize(t, valid_ids) for t in parsed.get("agreements", [])]  # type: ignore
    disagreements = [sanitize(t, valid_ids) for t in parsed.get("disagreements", [])]  # type: ignore
    uncertainties = list(parsed.get("uncertainties", []))  # type: ignore
    follow_ups = list(parsed.get("follow_ups", []))  # type: ignore

    used = apply_citations([summary, detail, *takeaways, *agreements, *disagreements], collector.sources)
    confidence = _compute_confidence(collector.sources, used, grounded=True)

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
    return answer, ModelInfo(model=persona.name, available=True, grounded=True)


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
                if not stripped or stripped.lower() in {"none", "n/a", "none.", "not applicable"}:
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


def _extractive_answer(query: str, sources: list[Source]) -> Answer:
    """Deterministic, source-grounded answer when no model is configured."""
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
