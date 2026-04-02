"""
Rate limiting middleware.
Per-IP sliding window. Configurable limits in settings.toml.
"""

import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

RATE_LIMIT = 60
RATE_WINDOW = 60

_request_counts: dict[str, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        window_start = now - RATE_WINDOW
        _request_counts[client_ip] = [
            t for t in _request_counts[client_ip] if t > window_start
        ]

        if len(_request_counts[client_ip]) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Try again later."},
                headers={
                    "X-RateLimit-Limit": str(RATE_LIMIT),
                    "X-RateLimit-Remaining": "0",
                },
            )

        _request_counts[client_ip].append(now)
        response = await call_next(request)
        remaining = RATE_LIMIT - len(_request_counts[client_ip])
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        return response


def get_rate_limit_middleware():
    return RateLimitMiddleware
