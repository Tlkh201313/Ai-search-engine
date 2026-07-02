"""Fast search endpoint (sources only, no answer synthesis)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import settings
from app.models import SearchRequest, SearchResponse
from app.research.dedupe import dedupe_search_results
from app.research.modes import get_mode
from app.search import multi_search
from app.security.ratelimit import rate_limit

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse, dependencies=[Depends(rate_limit)])
async def search(req: SearchRequest) -> SearchResponse:
    mode = get_mode(req.mode)
    results = await multi_search(
        [req.query], providers=settings.search_providers, limit=mode.search_limit
    )
    results = dedupe_search_results(results)[: req.limit]
    return SearchResponse(
        query=req.query,
        results=results,
        providers=settings.search_providers,
        total=len(results),
    )
