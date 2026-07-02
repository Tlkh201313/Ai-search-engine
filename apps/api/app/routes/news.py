"""Live news endpoint backing the frontend news page and home ticker."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.news import CATEGORIES, get_news

router = APIRouter(prefix="/api", tags=["news"])


@router.get("/news")
async def news(
    category: str = Query("top"),
    limit: int = Query(24, ge=1, le=40),
) -> dict:
    """Aggregated headlines from public feeds. Cached server-side (~10 min)."""
    items = await get_news(category, limit)
    return {
        "category": category if category in CATEGORIES else "top",
        "categories": CATEGORIES,
        "items": items,
    }
