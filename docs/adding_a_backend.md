# How to add a new search backend

## Quick start

1. Create a file in `backends/search/` or `plugins/connectors/`
2. Decorate with `@register` from `core.rotation`
3. Import it in `backends/search/__init__.py`

## Recommended pattern (with SearchResult)

```python
# backends/search/my_engine.py
from core.rotation import register
from core.agents import random_headers
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from backends.search.base import SearchResult

@register("my_engine", weight=1.0)
async def search(query: str, max_results: int, client):
    url = f"https://myengine.com/search?q={quote_plus(query)}"
    r = await client.get(url, headers=random_headers(), timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for res in soup.select(".result")[:max_results]:
        t = res.select_one(".title")
        s = res.select_one(".snippet")
        if t:
            results.append(SearchResult(
                title=t.get_text(strip=True),
                url=t.get("href", ""),
                snippet=s.get_text(strip=True) if s else "",
                source="my_engine",
            ).model_dump())
    return results
```

## Important notes

- **Use `SearchResult`**: Always wrap results with the `SearchResult` Pydantic model. This ensures consistent output and validates that `url` is present.
- **Circuit breaker**: Your backend automatically gets circuit breaker protection. After 3 consecutive failures, it will be skipped for 60 seconds.
- **Latency tracking**: All backend calls are automatically timed and exposed in `/stats` as p50/p95/p99 percentiles.
- **Weight**: Set `weight` in `@register("name", weight=1.0)` to influence how often your backend is picked. Higher = more frequent.

## In `backends/search/__init__.py`:

```python
from . import duckduckgo, brave, bing, mojeek, searxng, wiby, my_engine
```

Rotation + fallback work automatically — nothing else to change.

## Testing your backend

Add unit tests in `tests/unit/test_backends.py` that verify your selector patterns against sample HTML.
