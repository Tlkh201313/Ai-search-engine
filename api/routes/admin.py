from fastapi import APIRouter
from core.rotation import get_stats, REGISTRY, CIRCUITS, CircuitState
from cache.manager import clear as clear_cache, get_entry_count

router = APIRouter()


@router.get("/stats")
def stats():
    s = get_stats()
    total_searches = sum(v["uses"] for v in s.values())
    total_fails = sum(v["fails"] for v in s.values())
    return {
        "backends": s,
        "total_searches": total_searches,
        "total_fails": total_fails,
        "overall_success_rate": round(
            total_searches / max(total_searches + total_fails, 1), 3
        ),
    }


@router.get("/backends")
def backends():
    result = {}
    for name in REGISTRY:
        cb = CIRCUITS.get(name)
        result[name] = {
            "available": True,
            "circuit_state": cb.state.value if cb else "unknown",
            "weight": REGISTRY[name].get("weight", 1.0),
        }
    return {"available": list(REGISTRY.keys()), "details": result}


@router.delete("/cache")
async def wipe_cache():
    await clear_cache()
    return {"cleared": True}


@router.get("/health")
def health():
    backend_status = {}
    for name in REGISTRY:
        cb = CIRCUITS.get(name)
        backend_status[name] = (
            "healthy" if cb and cb.state == CircuitState.CLOSED else "degraded"
        )
    return {
        "status": "ok",
        "backends": backend_status,
    }


@router.get("/cache/stats")
async def cache_stats():
    count = await get_entry_count()
    return {"entries": count}
