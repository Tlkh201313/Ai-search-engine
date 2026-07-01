"""Health + readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.llm import get_persona, llm
from app.models import HealthResponse, ModelInfo

router = APIRouter(tags=["health"])


def _health() -> HealthResponse:
    persona = get_persona(settings.default_persona)
    return HealthResponse(
        status="ok",
        version=settings.version,
        environment=settings.environment,
        llm=ModelInfo(model=persona.name, available=llm.available(), grounded=llm.available()),
        search_providers=settings.search_providers,
    )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return _health()


@router.get("/api/health", response_model=HealthResponse)
async def api_health() -> HealthResponse:
    return _health()
