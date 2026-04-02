"""Test backend interface and result normalization."""

import pytest
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

from backends.search.base import BaseBackend, SearchResult


class TestSearchResult:
    def test_valid_result(self):
        r = SearchResult(
            title="Test", url="https://example.com", snippet="A snippet", source="test"
        )
        assert r.title == "Test"
        assert r.url == "https://example.com"

    def test_url_required(self):
        with pytest.raises(Exception):
            SearchResult()

    def test_model_dump(self):
        r = SearchResult(title="T", url="U", snippet="S", source="src")
        d = r.model_dump()
        assert d == {"title": "T", "url": "U", "snippet": "S", "source": "src"}


class TestBaseBackend:
    def test_normalize_valid_results(self):
        class DummyBackend(BaseBackend):
            name = "dummy"

            async def search(self, query, num_results, client):
                return []

        backend = DummyBackend()
        raw = [
            {"title": "A", "url": "https://a.com", "snippet": "Snip A", "source": "x"},
            {"title": "B", "url": "https://b.com", "snippet": "Snip B", "source": "y"},
        ]
        normalized = backend.normalize_results(raw)
        assert len(normalized) == 2
        assert normalized[0]["title"] == "A"
        assert normalized[1]["source"] == "y"

    def test_normalize_skips_invalid(self):
        class DummyBackend(BaseBackend):
            name = "dummy"

            async def search(self, query, num_results, client):
                return []

        backend = DummyBackend()
        raw = [
            {"title": "A", "url": "https://a.com", "snippet": "Snip", "source": "x"},
            {"bad": "data"},
        ]
        normalized = backend.normalize_results(raw)
        assert len(normalized) == 1
        assert normalized[0]["title"] == "A"
