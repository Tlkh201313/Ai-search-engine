"""Read + update non-secret runtime settings. Keys are never exposed or accepted."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.llm import llm
from app.models import ResearchMode, SettingsPublic, SettingsUpdate
from app.search.base import PROVIDERS

router = APIRouter(prefix="/api", tags=["settings"])


def _public() -> SettingsPublic:
    return SettingsPublic(
        llm_available=llm.available(),
        model=llm.model,
        grounded=llm.available(),
        search_providers=settings.search_providers,
        modes=[m.value for m in ResearchMode],
    )


@router.get("/settings", response_model=SettingsPublic)
async def get_settings() -> SettingsPublic:
    return _public()


@router.post("/settings", response_model=SettingsPublic)
async def update_settings(update: SettingsUpdate) -> SettingsPublic:
    if update.search_providers is not None:
        valid = [p for p in update.search_providers if p in PROVIDERS]
        if valid:
            settings.search_providers = valid
    return _public()
