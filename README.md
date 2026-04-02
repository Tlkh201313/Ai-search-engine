# ai-search-engine

Unlimited local AI web search server.
Rotates across 6+ backends. No API keys. Circuit-breaker protected.
Designed for AI models (Qwen, LLaMA, Mistral, etc.)

## Quick start

```bash
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open: http://localhost:8000/docs

## Features

- **6+ search backends**: DuckDuckGo, Brave, Bing, Mojeek, SearXNG, Wiby
- **Circuit breaker**: Each backend independently monitored; auto-skips failing backends
- **Exponential backoff**: Failed backends cool down with jitter
- **Smart caching**: SQLite (default) or Redis with per-query TTL and background eviction
- **SSE streaming**: `/search/stream` returns results as they arrive from each backend
- **LLM reranker**: Optional Ollama-based relevance scoring (toggle in settings.toml)
- **Semantic cache**: Optional vector-similarity cache for semantically similar queries
- **OpenAI + Anthropic tool schemas**: Both formats included
- **Rate limiting**: Per-IP protection against abuse
- **OpenTelemetry tracing**: Request IDs and latency tracking

## Endpoints

| Endpoint | Description |
|---|---|
| `GET /search` | Search with fallback rotation |
| `GET /search/all` | Query all backends simultaneously |
| `GET /search/stream` | SSE stream — results arrive as backends respond |
| `GET /fetch` | Fetch a page as clean text |
| `GET /scrape` | Scrape structured data from a page |
| `GET /stats` | Per-backend latency, success rate, circuit state |
| `GET /backends` | List available backends and their health |
| `GET /health` | Health check for load balancers |
| `DELETE /cache` | Wipe the cache |

## Folder layout

```
ai-search-engine/
├── api/              FastAPI app, routes, middleware, schemas
├── backends/         Search engines, fetchers, scrapers
│   └── search/       Each engine uses @register + SearchResult
├── cache/            SQLite + Redis with TTL and eviction
├── core/             Rotation engine with circuit breaker
├── plugins/          Drop-in upgrades (antigravity, connectors)
├── tools/            AI tool definitions (OpenAI + Anthropic)
├── tests/            Unit + integration tests (47 tests)
├── scripts/          Install helpers, SearXNG docker launch
├── config/           settings.toml + .env.example
└── docs/             Architecture notes, backend guides
```

## Connecting your AI

See `tools/tool_definitions.py` for the full tool schema (OpenAI + Anthropic).
See `tools/client_examples/` for Ollama, LM Studio, vLLM examples.

## Configuration

All settings in `config/settings.toml`. Key sections:

- `[rotation]` — strategy, circuit breaker thresholds, backoff settings
- `[cache]` — backend (sqlite/redis), TTL values, eviction interval
- `[reranker]` — enable LLM reranking, model name, Ollama URL
- `[semantic_cache]` — enable semantic caching, similarity threshold
- `[rate_limit]` — requests per minute

## Running tests

```bash
pytest tests/ -v
```

## Web UI

A full chat interface with settings panel. Run it with:

```bash
pip install streamlit
streamlit run ui/chat_app.py
```

Then open http://localhost:8501

**Features:**
- 💬 Chat-style search interface
- ⚙️ Settings sidebar — switch between Ollama (free) and Groq (cloud)
- 🦙 Ollama support — fully local, no API keys needed
- 📊 Result cards with title, snippet, source, and clickable links
- 🗑️ Clear chat history from sidebar
- ✅ Live server health indicator

### AI Provider Options

| Provider | Cost | Setup |
|----------|------|-------|
| **Ollama** (default) | Free | Install Ollama, pull a model (`ollama pull qwen2.5`) |
| **Groq** | Free tier | Add API keys in settings (supports multiple keys with auto-rotation) |
