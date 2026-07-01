"""Health + readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.llm import llm
from app.models import HealthResponse, ModelInfo

router = APIRouter(tags=["health"])


def _health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.version,
        environment=settings.environment,
        llm=ModelInfo(model=llm.model, available=llm.available(), grounded=llm.available()),
        search_providers=settings.search_providers,
    )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return _health()


@router.get("/api/health", response_model=HealthResponse)
async def api_health() -> HealthResponse:
    return _health()
