# Architecture

## Request flow

```
AI model (Qwen, LLaMA, etc.)
    │  tool call: web_search(query)
    ▼
FastAPI  /search  or  /search/stream
    │
    ├─► cache.manager ──── HIT ──► return cached result (fast)
    │        │ MISS
    ▼
core.rotation.run_with_fallback()
    │  checks circuit breaker for each backend
    │  picks least-recently-used healthy backend
    │  on fail → circuit breaker records failure
    │  after 3 consecutive failures → circuit opens (60s cooldown)
    │  tries all backends before giving up
    ▼
backends/search/<engine>.py   (duckduckgo / brave / bing / mojeek / searxng / wiby)
    │  each backend returns list[SearchResult] validated by Pydantic
    ▼
raw results list
    │
    ├─► cache.manager.set()  (per-query TTL from settings.toml)
    ├─► semantic cache check (optional, similarity > 0.92)
    ├─► LLM reranker (optional, Ollama-based)
    ▼
JSON response or SSE stream → AI model
```

## Circuit breaker states

Each backend has an independent circuit breaker:

| State | Behavior |
|---|---|
| `closed` | Backend is healthy, accepts requests |
| `open` | Backend failed 3+ times consecutively, skipped for 60s |
| `half_open` | Cooldown expired, one test request allowed |

## Extension points

| Goal | Where to add code |
|---|---|
| New search engine | `backends/search/` — inherit from `BaseBackend`, use `@register` |
| New page fetcher (JS, Tor) | `backends/fetch/` |
| Swap cache backend | `cache/` — implement get/set/clear, update manager.py |
| LLM reranker | `plugins/antigravity/llm_reranker.py` — toggle in settings.toml |
| Semantic cache | `plugins/antigravity/semantic_cache.py` — toggle in settings.toml |
| New AI client example | `tools/client_examples/` |
| Change rotation strategy | `config/settings.toml` → `[rotation] strategy` |
| Add tracing/metrics | `api/middleware/tracing.py` |

## Middleware stack

1. CORS (allow_origins from config)
2. OpenTelemetry tracing (request IDs, latency)
3. Rate limiting (per-IP, 60 req/min default)

## Tool schemas

- `tools/tool_definitions.py` provides both OpenAI and Anthropic formats
- Supports parallel tool calls and streaming responses
- See `OPENAI_TOOLS` and `ANTHROPIC_TOOLS` exports
