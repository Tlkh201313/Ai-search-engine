<div align="center">

# Lumen — a grounded AI research engine

**Ask anything and get a fast, source-backed answer with real citations.**
Lumen searches the web, reads the pages, ranks the evidence, streams its progress,
and writes an answer that cites only sources it actually read.

</div>

---

Lumen is an answer-first research engine that blends the strongest UX ideas from
modern AI products — source-backed answers and citations, a clean conversational
flow, and a calm, readable reading environment — into one original, premium
experience. It runs **free by default**: with no model configured it returns a
deterministic, source-grounded extract, and it upgrades to fully synthesized
answers the moment you point it at a hosted model.

## Features

- **Answer-first research** — a direct answer, a detailed explanation, key
  takeaways, points of agreement/disagreement, and honest uncertainty.
- **Real citations only** — every `[n]` maps to a source that was fetched and
  read. Citations to non-existent sources are stripped, not hallucinated.
- **Live research progress** — streamed over SSE: understanding → searching →
  finding sources → reading → deduping → ranking → writing → verifying.
- **Beautiful source cards** — citation number, domain, title, snippet, relevance
  score, and published/fetched date. No fake data.
- **Six research modes** — Quick, Deep, Compare, Latest News, Academic, and
  Code/Technical, each with its own search breadth, ranking weights, and prompt.
- **Free-first, no keys required** — DuckDuckGo + Wikipedia search out of the box;
  optional SearXNG, Brave, Bing, Mojeek.
- **One hosted model** — a single server-owned, Anthropic-Messages-compatible
  endpoint. End users never provide keys.
- **Fast & resilient** — async fetching, retries with backoff, per-provider
  isolation, SQLite caching of searches / pages / research sessions.
- **Secure by default** — SSRF-guarded fetching, request validation, rate
  limiting, scoped CORS, and no secrets in the client.
- **Calm, premium UI** — Next.js + Tailwind, dark/light, mobile-first, keyboard
  shortcuts, skeletons, and smooth streaming states.

## Screenshots

> Home, streaming research, and the answer + source panel.
> _(Add PNGs under `docs/screenshots/` — the UI is shown live at `http://localhost:3000`.)_

| Home | Answer + sources |
| --- | --- |
| `docs/screenshots/home.png` | `docs/screenshots/answer.png` |

## Architecture

```
┌────────────────────────┐         ┌──────────────────────────────────────────┐
│  apps/web (Next.js)     │  HTTP   │  apps/api (FastAPI)                        │
│  ───────────────────    │ ───────▶│  ────────────────────                      │
│  • Home / search        │         │  POST /api/research  ── creates a session  │
│  • Research view        │◀─ SSE ──│  GET  /api/research/{id}/stream (progress) │
│  • Source panel         │         │                                            │
│  • Streaming answer      │         │   Research pipeline:                       │
└────────────────────────┘         │   understand → search (N providers,        │
                                     │   concurrent) → dedupe → fetch+extract →   │
                                     │   dedupe content → rank → answer → verify  │
                                     │        │            │           │         │
                                     │   ┌────▼────┐  ┌────▼────┐  ┌───▼─────┐   │
                                     │   │ search/ │  │ fetch/  │  │  llm/   │   │
                                     │   │ (DDG,   │  │ httpx + │  │ 1 hosted│   │
                                     │   │  wiki,  │  │ readable│  │  model  │   │
                                     │   │  …)     │  │ extract │  │(optional)│  │
                                     │   └─────────┘  └─────────┘  └─────────┘   │
                                     │   SQLite cache · SSRF guard · rate limit   │
                                     └──────────────────────────────────────────┘
```

The contract between the two apps is defined once in
[`apps/api/app/models.py`](apps/api/app/models.py) (Pydantic) and mirrored in
[`apps/web/src/lib/types.ts`](apps/web/src/lib/types.ts). See
[`docs/architecture.md`](docs/architecture.md) for the full pipeline write-up.

```
Ai-search-engine/
├── apps/
│   ├── api/            FastAPI backend (search, fetch, rank, cite, stream)
│   │   ├── app/        config · models · cache · search · fetch · research · llm · routes · security
│   │   └── tests/      pytest suite (dedupe, rank, ssrf, citations, search, pipeline, api)
│   └── web/            Next.js + TypeScript + Tailwind frontend
│       └── src/        app (routes) · components · hooks · lib
├── docs/               architecture notes
├── docker-compose.yml  optional: SearXNG for unlimited key-free search
├── Makefile            convenience commands
└── README.md
```

## Requirements

- **Python** 3.11+
- **Node** 18+ and **pnpm** (or npm)
- Optional: **Docker** (for a local SearXNG instance)
- Optional: a hosted **Anthropic-Messages-compatible** model endpoint for
  synthesized answers

## Quick start

### 1. Backend

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # optional; sane defaults
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs for the interactive API, or
http://localhost:8000/health for a status check.

### 2. Frontend

```bash
cd apps/web
pnpm install                # or: npm install
cp .env.example .env.local  # NEXT_PUBLIC_API_URL=http://localhost:8000
pnpm dev
```

Open http://localhost:3000.

That's it — the app is fully functional in **extractive mode** (answers quoted
directly from ranked sources) with no API keys.

## Enabling synthesized answers (one hosted model)

Lumen uses **one** server-owned model behind **one** base URL that speaks the
Anthropic Messages API. Set these in `apps/api/.env` and restart the backend:

```bash
LLM_BASE_URL=https://your-endpoint.example.com   # Anthropic-compatible base URL
LLM_API_KEY=sk-...                               # your key (server-side only)
LLM_MODEL=claude-sonnet-5                         # whatever your endpoint serves
```

- The client `POST`s to `${LLM_BASE_URL}/v1/messages` with `x-api-key` +
  `anthropic-version` headers (and a `Bearer` header for proxies that want it).
- With no key, or `LLM_API_KEY=dummy`, Lumen stays in extractive mode and never
  crashes.
- Keys live only in the backend `.env`. They are never sent to the browser and
  never exposed via `/api/settings`.

## Optional: SearXNG for unlimited, key-free meta-search

```bash
docker compose up -d searxng          # or: docker run -d -p 8888:8080 searxng/searxng
# apps/api/.env:
SEARXNG_URL=http://localhost:8888
SEARCH_PROVIDERS=searxng,wikipedia
```

## Commands

Backend (from `apps/api`, venv active):

| Command | Purpose |
| --- | --- |
| `uvicorn app.main:app --reload` | run the API |
| `pytest` | run the test suite |
| `ruff check app` | lint |
| `ruff format app` | format |

Frontend (from `apps/web`):

| Command | Purpose |
| --- | --- |
| `pnpm dev` | run the app |
| `pnpm build` | production build |
| `pnpm typecheck` | TypeScript check |
| `pnpm lint` | ESLint |
| `pnpm format` | Prettier |

Or use the root **Makefile**: `make api-install`, `make api-test`, `make web-dev`,
`make web-build`, …

## API

| Method & path | Description |
| --- | --- |
| `GET /health` | service + model + provider status |
| `POST /api/search` | fast source search (no answer) |
| `POST /api/research` | start a research run → `{ id }` |
| `GET /api/research/{id}/stream` | SSE stream of progress + final result |
| `GET /api/research/{id}` | final result (when complete) |
| `POST /api/fetch` | fetch + extract one page (SSRF-guarded) |
| `GET /api/sources?research_id=` | ranked sources for a run |
| `GET /api/settings` · `POST /api/settings` | non-secret runtime settings |

## Research modes

| Mode | Focus |
| --- | --- |
| **Quick** | fast answer, few strong sources |
| **Deep** | broad search, more sources, thorough synthesis |
| **Compare** | surfaces agreement vs. disagreement across sources |
| **Latest News** | prioritizes freshness and reputable reporting |
| **Academic** | favors papers, references, authoritative domains |
| **Code / Technical** | favors docs, GitHub, technical Q&A |

## Troubleshooting

- **“Running in extractive mode.”** No model is configured — set `LLM_BASE_URL` /
  `LLM_API_KEY`. This is expected and not an error.
- **“Can't reach the API.”** Start the backend and confirm `NEXT_PUBLIC_API_URL`
  in `apps/web/.env.local` matches it.
- **Searches return 0 sources.** Your network may block search engines, or a
  provider is rate-limited. Add `SEARXNG_URL` and switch `SEARCH_PROVIDERS`.
- **Fetch says “blocked”.** SSRF protection blocked a private/loopback address.
  For local testing only, set `ALLOW_PRIVATE_IPS=true`.
- **CORS errors.** Add your web origin to `CORS_ORIGINS` in `apps/api/.env`.

## Security notes

- No secrets in the frontend; the LLM key is backend-only and never returned by
  any endpoint.
- Fetch/scrape endpoints validate URLs and block private, loopback, link-local,
  and reserved IP ranges (SSRF) unless `ALLOW_PRIVATE_IPS=true`.
- Expensive endpoints (`/api/research`, `/api/fetch`) are rate-limited per IP.
- CORS is restricted to configured origins (not `*`).
- All request bodies are validated with Pydantic.

## Roadmap

- Streaming synthesized answers with per-sentence citation highlighting
- Redis cache backend + shared multi-instance sessions
- PDF / arXiv full-text ingestion for Academic mode
- Optional embeddings reranker for relevance
- Exportable research reports (Markdown / PDF)
- Saved research history synced across devices

## License

MIT — see [LICENSE](LICENSE).
