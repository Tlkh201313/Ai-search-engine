"""
Drop-in connector slot. Add a new search source by creating a file here.
Each connector must define an async search(query, max_results, client) function
and call @register("name") from core.rotation.

Template:

    from core.rotation import register
    from core.agents import random_headers

    @register("my_engine", weight=1.0)
    async def search(query: str, max_results: int, client):
        # ... hit source, return [{title, url, snippet, source}]
        return results

Then import it in backends/search/__init__.py:
    from . import duckduckgo, brave, ..., my_engine
"""
