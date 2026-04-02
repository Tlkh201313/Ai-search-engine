"""FastAPI entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.routes import search, fetch, scrape, admin
from cache.manager import init as init_cache
import backends.search
from api.middleware.tracing import get_tracing_middleware
from api.middleware.rate_limit import get_rate_limit_middleware

app = FastAPI(title="Unlimited AI Search Server", version="2.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
app.add_middleware(get_tracing_middleware())
app.add_middleware(get_rate_limit_middleware())


@app.on_event("startup")
async def startup():
    await init_cache()


app.include_router(search.router)
app.include_router(fetch.router)
app.include_router(scrape.router)
app.include_router(admin.router)

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    pass


@app.get("/")
def root():
    from fastapi.responses import FileResponse
    import os

    index_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "static", "index.html"
    )
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
