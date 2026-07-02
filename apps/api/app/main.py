"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.cache import cache
from app.config import settings
from app.logging import configure_logging, get_logger
from app.routes import routers

configure_logging()
log = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.init()
    # Import search providers so they self-register.
    import app.search  # noqa: F401

    log.info(
        "%s v%s ready — providers=%s llm=%s",
        settings.app_name,
        settings.version,
        ",".join(settings.search_providers),
        "on" if settings.llm_configured else "extractive-fallback",
    )
    yield
    await cache.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Grounded AI research engine — search, read, rank, and cite the web.",
    lifespan=lifespan,
)

# Compress large JSON payloads (news, research results) — big win on slow links.
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

for router in routers:
    app.include_router(router)


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "health": "/health",
        "endpoints": [
            "POST /api/search",
            "POST /api/research",
            "GET /api/research/{id}/stream",
            "GET /api/research/{id}",
            "POST /api/fetch",
            "GET /api/sources?research_id=",
            "GET /api/settings",
            "GET /api/news?category=&limit=",
        ],
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})
