"""
LLM-based reranker using a local Ollama model.
Scores and reorders search results by relevance to the query.
Toggle in settings.toml: [reranker] enabled = true
"""

import os
import json
import httpx

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("RERANKER_MODEL", "qwen2.5")
PROMPT_TEMPLATE = """You are a relevance scorer. Given a query and a search result, score how relevant the result is on a scale of 0 to 100.
Return ONLY a JSON number. No explanation.

Query: {query}
Title: {title}
Snippet: {snippet}
URL: {url}

Score:"""


async def score_result(query: str, result: dict, model: str = DEFAULT_MODEL) -> float:
    prompt = PROMPT_TEMPLATE.format(
        query=query,
        title=result.get("title", ""),
        snippet=result.get("snippet", ""),
        url=result.get("url", ""),
    )
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0, "num_predict": 10},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            text = data.get("response", "0").strip()
            score = float(text)
            return max(0.0, min(100.0, score))
    except Exception:
        return 50.0


async def rerank(query: str, results: list, model: str = DEFAULT_MODEL) -> list:
    if not results:
        return results

    scored = []
    tasks = []
    for r in results:
        tasks.append(score_result(query, r, model))
    scores = await asyncio.gather(*tasks, return_exceptions=True)

    for r, s in zip(results, scores):
        if isinstance(s, Exception):
            s = 50.0
        scored.append({**r, "relevance_score": s})

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored


import asyncio
