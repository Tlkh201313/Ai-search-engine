"""
Antigravity upgrade slots.
Drop future capabilities here without touching core code.

Planned:
  proxy_rotator.py     — Rotate proxies to avoid IP bans at high volume
  llm_reranker.py      — Local LLM reranks results by true relevance
  semantic_cache.py    — Vector similarity cache (near-duplicate query hits)
  google_api.py        — Google Custom Search API wrapper
  tor_backend.py       — Route through Tor for anonymity
  stream_results.py    — SSE streaming for long-running searches
"""
