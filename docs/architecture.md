# Architecture

Lumen is a two-app monorepo: a **FastAPI** backend (`apps/api`) that does the
research, and a **Next.js** frontend (`apps/web`) that renders it. The wire
contract is defined once in `apps/api/app/models.py` (Pydantic) and mirrored in
`apps/web/src/lib/types.ts`.

## Request lifecycle

1. The browser `POST`s `{ query, mode }` to `/api/research`. The backend creates
   an in-memory **session** with an event buffer, kicks off the pipeline as a
   background task, and returns `{ id }` immediately.
2. The browser opens an **EventSource** on `/api/research/{id}/stream`. The
   backend replays every buffered `ProgressEvent` from the start (so nothing is
   missed) and then streams new ones until `done`/`error`.
3. The final `done` event carries the complete `ResearchResult`. It is also
   cached and retrievable via `GET /api/research/{id}`.

Using create-then-stream (instead of streaming from the POST) means the frontend
can use the native `EventSource` API, and a reload can re-attach or fall back to
the cached final result.

## The pipeline (`app/research/pipeline.py`)

```
understanding → searching → finding_sources → reading →
deduping → ranking → writing → verifying → done
```

Each stage emits a typed `ProgressEvent` (stage, status, message, progress, data).

1. **Understanding** — validate the query; if a model is configured and the mode
   asks for it, expand into a few sub-queries.
2. **Searching** — run all enabled providers concurrently for every (sub-)query
   with per-provider timeouts; one provider failing never fails the run
   (`app/search/aggregator.py`).
3. **Finding sources** — dedupe search hits by normalized URL and near-identical
   title (`app/research/dedupe.py`).
4. **Reading** — fetch the top-N candidates concurrently (bounded semaphore),
   extract clean text + metadata (`app/fetch/`).
5. **Deduping** — drop pages whose *content* is near-duplicate (token-set
   Jaccard over a fingerprint).
6. **Ranking** — score every readable page and keep the mode's `max_sources`,
   assigning 1-based citation ids (`app/research/rank.py`).
7. **Writing** — build a grounded prompt with the numbered sources and stream the
   answer. With no model, produce a deterministic extractive answer instead.
8. **Verifying** — parse `[n]` citations, strip any that point to a non-existent
   source, and mark the sources actually used (`app/research/citations.py`).

## Ranking

Each source gets four sub-scores in `[0, 1]`, combined with mode-specific weights:

- **relevance** — query-keyword overlap with title + body (title weighted higher).
- **freshness** — exponential decay on the published date (unknown ⇒ neutral).
- **quality** — curated domain-reputation prior, `.gov`/`.edu` boost, per-mode
  preferred-domain bonus, short-content penalty.
- **depth** — log-scaled word count.

`build_excerpt()` then selects the passages most relevant to the query (not the
whole page) to keep the LLM prompt focused and cheap.

## Citations (the trust contract)

- The model is instructed to cite only the numbered sources it was given.
- `sanitize()` removes any `[n]` where `n` is out of range — hallucinated
  citations can't survive.
- `apply_citations()` records which sources were actually referenced and marks
  them `used`; those get a dot in the UI and can't be silently dropped.
- Confidence is derived from the quality and count of the *used* sources and
  whether an LLM synthesized the answer.

## The model layer (`app/llm/`)

One hosted model behind one Anthropic-Messages-compatible base URL, owned by the
operator. `LLMClient.available()` is false until `LLM_BASE_URL` + a real
`LLM_API_KEY` are set; until then the pipeline uses its extractive fallback and
never crashes. Keys live only in the backend and are never exposed by any
endpoint.

## Caching (`app/cache/`)

A small async cache with a SQLite backend (default) or in-memory fallback, keyed
by a hash of the inputs, with per-entry TTL and lazy eviction. Searches, fetched
pages, and completed research sessions are all cached, so repeat queries and
shared source pages are near-instant.

## Security

- **SSRF** (`app/security/ssrf.py`): every fetched URL must be http(s) and must
  not resolve to a private, loopback, link-local, or reserved address unless
  `ALLOW_PRIVATE_IPS=true`. Hostnames are resolved and every returned address is
  checked.
- **Rate limiting** (`app/security/ratelimit.py`): sliding-window per client IP
  on the expensive endpoints.
- **CORS**: restricted to configured origins.
- **Validation**: all request bodies are Pydantic models with bounds.

## Frontend

- `app/page.tsx` — the home/search screen.
- `app/research/[id]/page.tsx` — a conversation of **turns**. Each `Turn` owns a
  `useResearch` hook that streams one run; the page shows the active turn's
  sources in a sticky panel (desktop) or a drawer (mobile).
- `components/Markdown.tsx` renders the answer and converts inline `[n]` tokens
  into interactive citation chips that scroll to and highlight the source card —
  without allowing raw HTML.
- Theme, history, and modes live in `lib/`.
