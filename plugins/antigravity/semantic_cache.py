"""
Semantic cache using sentence-transformers.
Finds cached results for semantically similar queries.
"latest AI news" hits cache for "recent artificial intelligence news".

Requires: pip install sentence-transformers numpy
"""

import os
import json
import time
import pathlib
import numpy as np

CACHE_DB_PATH = pathlib.Path(__file__).parent / "semantic_cache.db"
DEFAULT_SIMILARITY_THRESHOLD = 0.92
DEFAULT_MODEL = os.getenv("SEMANTIC_MODEL", "all-MiniLM-L6-v2")

_model = None
_embeddings = {}
_entries = {}


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(DEFAULT_MODEL)
        except ImportError:
            return None
    return _model


def _encode(text: str) -> np.ndarray | None:
    model = _get_model()
    if model is None:
        return None
    return model.encode(text, convert_to_numpy=True)


async def init():
    global _entries
    db_path = CACHE_DB_PATH
    if db_path.exists():
        try:
            with open(db_path, "r") as f:
                data = json.load(f)
                for key, val in data.items():
                    _entries[key] = val
        except Exception:
            _entries = {}


async def _persist():
    try:
        with open(CACHE_DB_PATH, "w") as f:
            json.dump(_entries, f)
    except Exception:
        pass


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


async def get(
    query: str, ttl: int = 3600, threshold: float = DEFAULT_SIMILARITY_THRESHOLD
):
    embedding = _encode(query)
    if embedding is None:
        return None

    best_key = None
    best_score = 0.0
    now = time.time()

    for key, entry in _entries.items():
        if now - entry.get("ts", 0) > ttl:
            continue
        cached_embedding = np.array(entry["embedding"])
        sim = _cosine_similarity(embedding, cached_embedding)
        if sim > best_score and sim >= threshold:
            best_score = sim
            best_key = key

    if best_key is not None:
        result = _entries[best_key]["value"]
        result["semantic_match"] = True
        result["similarity"] = round(best_score, 4)
        result["matched_query"] = best_key
        return result
    return None


async def set(query: str, value, ttl: int = 3600):
    embedding = _encode(query)
    if embedding is None:
        return
    _entries[query] = {
        "value": value,
        "embedding": embedding.tolist(),
        "ts": time.time(),
        "ttl": ttl,
    }
    await _persist()


async def clear():
    global _entries
    _entries = {}
    if CACHE_DB_PATH.exists():
        CACHE_DB_PATH.unlink()
