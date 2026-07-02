"""Lightweight in-memory sliding-window rate limiter (per client IP)."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import settings


class RateLimiter:
    def __init__(self, per_minute: int) -> None:
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, client_id: str) -> None:
        if self.per_minute <= 0:
            return
        now = time.time()
        window = self._hits[client_id]
        cutoff = now - 60
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= self.per_minute:
            retry = max(1, int(60 - (now - window[0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
                headers={"Retry-After": str(retry)},
            )
        window.append(now)


_limiter = RateLimiter(settings.rate_limit_per_minute)


def _client_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit(request: Request) -> None:
    """FastAPI dependency guarding expensive endpoints."""
    _limiter.check(_client_id(request))
