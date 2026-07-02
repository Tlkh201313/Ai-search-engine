"""In-memory research session registry with live event buffers."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.models import (
    ConversationTurn,
    ProgressEvent,
    ProgressStage,
    ResearchMode,
    ResearchResult,
)

_MAX_SESSIONS = 200
_SESSION_TTL = 1800  # seconds
_HEARTBEAT = 15  # seconds between keep-alive pings


@dataclass
class ResearchSession:
    id: str
    query: str
    mode: ResearchMode
    persona: str = ""
    context: list[ConversationTurn] = field(default_factory=list)
    status: str = "running"  # running | complete | error
    created_at: float = field(default_factory=time.time)
    result: ResearchResult | None = None
    events: list[ProgressEvent] = field(default_factory=list)
    _updated: asyncio.Event = field(default_factory=asyncio.Event)

    def emit(self, event: ProgressEvent) -> None:
        self.events.append(event)
        self._updated.set()

    def finish(self, result: ResearchResult) -> None:
        self.result = result
        self.status = result.status
        self._updated.set()

    async def stream(self) -> AsyncIterator[ProgressEvent]:
        idx = 0
        while True:
            while idx < len(self.events):
                yield self.events[idx]
                idx += 1
            if self.status != "running":
                return
            self._updated.clear()
            if idx < len(self.events):
                continue
            try:
                await asyncio.wait_for(self._updated.wait(), timeout=_HEARTBEAT)
            except TimeoutError:
                last_stage = self.events[-1].stage if self.events else ProgressStage.searching
                yield ProgressEvent(
                    stage=last_stage,
                    status="active",
                    message="",
                    data={"heartbeat": True},
                )


class SessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[str, ResearchSession] = {}

    def create(
        self,
        query: str,
        mode: ResearchMode,
        persona: str = "",
        context: list[ConversationTurn] | None = None,
    ) -> ResearchSession:
        self._prune()
        session = ResearchSession(
            id=uuid.uuid4().hex[:16], query=query, mode=mode, persona=persona, context=context or []
        )
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> ResearchSession | None:
        return self._sessions.get(session_id)

    def _prune(self) -> None:
        now = time.time()
        stale = [
            sid for sid, s in self._sessions.items()
            if s.status != "running" and now - s.created_at > _SESSION_TTL
        ]
        for sid in stale:
            self._sessions.pop(sid, None)
        if len(self._sessions) > _MAX_SESSIONS:
            oldest = sorted(self._sessions.values(), key=lambda s: s.created_at)
            for s in oldest[: len(self._sessions) - _MAX_SESSIONS]:
                self._sessions.pop(s.id, None)


sessions = SessionRegistry()
