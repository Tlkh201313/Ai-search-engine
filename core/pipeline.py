"""
Post-processing pipeline for search results.

Two optional, config-gated stages sit between a raw backend response and the
caller:

* **Reranker** — an LLM (via Ollama) scores each result for relevance and
  reorders them. Enabled with ``[reranker] enabled = true``.
* **Semantic cache** — a vector-similarity cache that serves results for
  queries that *mean* the same thing, not just byte-identical ones. Enabled
  with ``[semantic_cache] enabled = true``.

Both stages degrade gracefully: if the optional dependency is missing or the
service is unreachable, the original results pass through untouched. They are
disabled by default, so the hot path stays dependency-free.
"""

from typing import Optional

from core.config import CFG

_rerank_cfg = CFG.get("reranker", {})
_sem_cfg = CFG.get("semantic_cache", {})

RERANK_ENABLED = bool(_rerank_cfg.get("enabled", False))
RERANK_MODEL = _rerank_cfg.get("model", "qwen2.5")

SEMANTIC_ENABLED = bool(_sem_cfg.get("enabled", False))
SEMANTIC_THRESHOLD = float(_sem_cfg.get("similarity_threshold", 0.92))

_semantic_ready = False


async def rerank(query: str, results: list) -> list:
    """Reorder results by LLM-judged relevance, if the reranker is enabled."""
    if not RERANK_ENABLED or not results:
        return results
    try:
        from plugins.antigravity.llm_reranker import rerank as _rerank

        return await _rerank(query, results, model=RERANK_MODEL)
    except Exception:
        return results


async def _ensure_semantic():
    global _semantic_ready
    if _semantic_ready:
        return True
    try:
        from plugins.antigravity import semantic_cache

        await semantic_cache.init()
        _semantic_ready = True
        return True
    except Exception:
        return False


async def semantic_lookup(query: str, ttl: int) -> Optional[dict]:
    """Return a semantically-similar cached response, or ``None``."""
    if not SEMANTIC_ENABLED:
        return None
    if not await _ensure_semantic():
        return None
    try:
        from plugins.antigravity import semantic_cache

        hit = await semantic_cache.get(query, ttl=ttl, threshold=SEMANTIC_THRESHOLD)
        if hit:
            hit["cached"] = True
            return hit
    except Exception:
        return None
    return None


async def semantic_store(query: str, value: dict, ttl: int) -> None:
    if not SEMANTIC_ENABLED:
        return
    if not await _ensure_semantic():
        return
    try:
        from plugins.antigravity import semantic_cache

        await semantic_cache.set(query, value, ttl=ttl)
    except Exception:
        pass
