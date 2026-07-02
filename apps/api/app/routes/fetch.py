"""Single-page fetch + extraction endpoint (SSRF-guarded)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.fetch import fetch_page
from app.models import FetchRequest, FetchResponse
from app.security.ratelimit import rate_limit

router = APIRouter(prefix="/api", tags=["fetch"])


@router.post("/fetch", response_model=FetchResponse, dependencies=[Depends(rate_limit)])
async def fetch(req: FetchRequest) -> FetchResponse:
    page = await fetch_page(str(req.url), max_chars=req.max_chars)
    if not page.ok:
        raise HTTPException(status_code=422, detail=page.error or "failed to fetch page")
    return FetchResponse(
        url=page.url,
        title=page.title,
        domain=page.domain,
        text=page.text,
        author=page.author,
        description=page.description,
        published_at=page.published_at,
        word_count=page.word_count,
    )
