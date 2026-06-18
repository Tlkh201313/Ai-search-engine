"""
Rate limiting middleware.
Per-IP sliding window. Limit configurable via settings.toml [rate_limit].
"""

import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.config import CFG

RATE_LIMIT = int(CFG.get("rate_limit", {}).get("requests_per_minute", 60))
RATE_WINDOW = 60

# Endpoints that must never be throttled (load-balancer probes, landing page).
EXEMPT_PATHS = {"/health", "/"}

_request_counts: dict[str, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - RATE_WINDOW

        recent = [t for t in _request_counts[client_ip] if t > window_start]

        if len(recent) >= RATE_LIMIT:
            _request_counts[client_ip] = recent
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Try again later."},
                headers={
                    "X-RateLimit-Limit": str(RATE_LIMIT),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(RATE_WINDOW),
                },
            )

        recent.append(now)
        # Drop the key when idle so the map can't grow without bound.
        if recent:
            _request_counts[client_ip] = recent
        else:
            _request_counts.pop(client_ip, None)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(max(0, RATE_LIMIT - len(recent)))
        return response


def get_rate_limit_middleware():
    return RateLimitMiddleware
