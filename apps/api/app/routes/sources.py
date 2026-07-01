"""Return the ranked sources for a completed research session."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.models import Source
from app.research import sessions

router = APIRouter(prefix="/api", tags=["sources"])


@router.get("/sources", response_model=list[Source])
async def get_sources(research_id: str = Query(..., description="research session id")) -> list[Source]:
    session = sessions.get(research_id)
    if session is None or session.result is None:
        raise HTTPException(status_code=404, detail="no sources for this research id")
    return session.result.sources
