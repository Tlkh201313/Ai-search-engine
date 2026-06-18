"""FastAPI entrypoint."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import search, fetch, scrape, admin
from api.middleware.tracing import get_tracing_middleware
from api.middleware.rate_limit import get_rate_limit_middleware
from cache.manager import init as init_cache, shutdown as shutdown_cache
import backends.search  # noqa: F401 — imported for backend self-registration

_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_cache()
    yield
    await shutdown_cache()


app = FastAPI(title="Unlimited AI Search Server", version="2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
app.add_middleware(get_tracing_middleware())
app.add_middleware(get_rate_limit_middleware())

app.include_router(search.router)
app.include_router(fetch.router)
app.include_router(scrape.router)
app.include_router(admin.router)

if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/")
def root():
    index_path = os.path.join(_STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "status": "running",
        "docs": "/docs",
        "endpoints": [
            "/search",
            "/search/all",
            "/search/stream",
            "/fetch",
            "/scrape",
            "/stats",
            "/backends",
            "/cache",
            "/health",
        ],
    }
