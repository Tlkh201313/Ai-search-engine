# Making it truly unlimited

## Tier 1 — Default (works out of the box)
6 backends rotate automatically. Each request goes to a different engine.
No API keys needed.

## Tier 2 — Run your own SearXNG (recommended)
SearXNG queries Google, Bing, DuckDuckGo, and 70+ others simultaneously.
Running it locally = zero external rate limits.

```bash
bash scripts/run_searxng_docker.sh
```

Then in `.env`:
```
SEARXNG_URL=http://localhost:8888
```

## Tier 3 — Add proxy rotation (plugins/antigravity/proxy_rotator.py)
Rotate IPs so no single source can rate-limit by IP.
Use paid proxies (Bright Data, Oxylabs) for production reliability.

## Tier 4 — Redis cache
Switch from SQLite to Redis for faster cache + multi-process sharing.
```
CACHE_BACKEND=redis
REDIS_URL=redis://localhost:6379
```

## Tier 5 — LLM reranking (plugins/antigravity/llm_reranker.py)
After fetching results from all backends, ask a local LLM to score 
each result for relevance to the original query. Slower, but much 
higher quality — especially for complex research queries.
