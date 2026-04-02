"""Integration tests for API endpoints with mocked backends."""

import pytest
import asyncio
import json
from httpx import ASGITransport, AsyncClient
from api.main import app
from core import rotation


@pytest.fixture(autouse=True)
def clean_registry():
    rotation.REGISTRY.clear()
    rotation.CIRCUITS.clear()
    rotation.METRICS.clear()

    @rotation.register("test_backend", weight=1.0)
    async def test_search(query, max_results, client):
        return [
            {
                "title": f"Result {i} for {query}",
                "url": f"https://example.com/{i}",
                "snippet": f"Snippet {i}",
                "source": "test_backend",
            }
            for i in range(max_results)
        ]

    yield


@pytest.mark.asyncio
async def test_search_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/search", params={"q": "test query", "max_results": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) == 3
        assert data["backend_used"] == "test_backend"
        assert data["query"] == "test query"


@pytest.mark.asyncio
async def test_search_all_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/search/all", params={"q": "test query", "max_results": 2}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "backends_queried" in data


@pytest.mark.asyncio
async def test_stream_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/search/stream", params={"q": "test query", "max_results": 2}
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"
        body = resp.text
        assert "event" in body
        assert "results" in body or "done" in body


@pytest.mark.asyncio
async def test_stats_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "backends" in data
        assert "total_searches" in data
        assert "overall_success_rate" in data


@pytest.mark.asyncio
async def test_backends_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/backends")
        assert resp.status_code == 200
        data = resp.json()
        assert "available" in data
        assert "test_backend" in data["available"]
        assert "details" in data


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "backends" in data


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert "/search/stream" in data["endpoints"]


@pytest.mark.asyncio
async def test_cache_wipe_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.delete("/cache")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cleared"] is True
