"""Run the API with `python -m app`, honoring API_HOST / API_PORT from .env.

This makes the configured port the single source of truth: change `API_PORT` in
`.env` (and `NEXT_PUBLIC_API_URL` in the web app) and both `python -m app` and
the dev launcher pick it up — no need to remember `uvicorn ... --port` flags.
"""

from __future__ import annotations

import uvicorn

from app.config import settings


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=not settings.is_production,
    )


if __name__ == "__main__":
    main()
