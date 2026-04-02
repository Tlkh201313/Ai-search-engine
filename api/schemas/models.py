from pydantic import BaseModel
from typing import List, Optional

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source: str

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    backend_used: Optional[str] = None
    tried: List[str] = []
    cached: bool = False
