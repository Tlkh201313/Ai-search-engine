"""Research endpoints: create, stream progress (SSE), fetch final result."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.llm import get_persona
from app.models import ResearchCreated, ResearchRequest, ResearchResult
from app.research import run_research, sessions
from app.security.ratelimit import rate_limit

router = APIRouter(prefix="/api", tags=["research"])

# Keep strong references to background tasks so they are not garbage-collected.
_tasks: set[asyncio.Task] = set()

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # disable proxy buffering (nginx)
}


@router.post("/research", response_model=ResearchCreated, dependencies=[Depends(rate_limit)])
async def create_research(req: ResearchRequest) -> ResearchCreated:
    persona = get_persona(req.persona).key  # normalize / validate
    session = sessions.create(req.query, req.mode, persona=persona, context=req.context)
    task = asyncio.create_task(run_research(session))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return ResearchCreated(id=session.id, query=req.query, mode=req.mode, persona=persona)


@router.get("/research/{research_id}/stream")
async def stream_research(research_id: str) -> StreamingResponse:
    session = sessions.get(research_id)
    if session is None:
        raise HTTPException(status_code=404, detail="research session not found")

    async def event_generator():
        async for event in session.stream():
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(), media_type="text/event-stream", headers=_SSE_HEADERS
    )


@router.get("/research/{research_id}", response_model=ResearchResult)
async def get_research(research_id: str) -> ResearchResult:
    session = sessions.get(research_id)
    if session is None:
        raise HTTPException(status_code=404, detail="research session not found")
    if session.result is None:
        raise HTTPException(status_code=202, detail="research is still running")
    return session.result
