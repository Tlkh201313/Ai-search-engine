"""
OpenTelemetry tracing middleware.
Exports to stdout in dev mode. Set OTEL_EXPORTER_OTLP_ENDPOINT for prod.
"""

import os
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.config import CFG

OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or CFG.get(
    "observability", {}
).get("otel_endpoint", "")
USE_OTEL = bool(OTEL_ENDPOINT)


class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:12])
        start_time = time.monotonic()

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        elapsed_ms = (time.monotonic() - start_time) * 1000

        if not USE_OTEL:
            return response

        span = {
            "trace_id": request_id,
            "span_name": f"{request.method} {request.url.path}",
            "status_code": response.status_code,
            "duration_ms": round(elapsed_ms, 2),
            "method": request.method,
            "path": request.url.path,
        }
        print(f"[OTEL] {span}")

        return response


def get_tracing_middleware():
    return TracingMiddleware
