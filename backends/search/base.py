"""
Abstract base class for all search backends.
Every engine must implement async search(query, num_results, client) -> list[dict].
"""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    title: str = Field(default="")
    url: str
    snippet: str = Field(default="")
    source: str = Field(default="")


class BaseBackend(ABC):
    name: str = ""
    weight: float = 1.0

    @abstractmethod
    async def search(self, query: str, num_results: int, client: Any) -> list[dict]:
        """Search the backend and return a list of result dicts."""
        ...

    def normalize_results(self, raw_results: list[dict]) -> list[dict]:
        normalized = []
        for r in raw_results:
            try:
                validated = SearchResult(**r)
                normalized.append(validated.model_dump())
            except Exception:
                continue
        return normalized
