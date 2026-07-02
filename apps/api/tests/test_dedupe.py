from app.fetch.fetcher import FetchedPage
from app.research.dedupe import dedupe_pages, dedupe_search_results


def test_dedupe_search_results_by_url(sample_results):
    deduped = dedupe_search_results(sample_results)
    # python.org, www.python.org and python.org normalize to the same URL.
    urls = {r.url for r in deduped}
    assert len(deduped) == 2
    assert "https://en.wikipedia.org/wiki/Python" in urls


def test_dedupe_pages_removes_near_duplicates():
    text = "the quick brown fox jumps over the lazy dog " * 30
    pages = [
        FetchedPage(url="https://a.com", ok=True, text=text, word_count=270),
        FetchedPage(url="https://b.com", ok=True, text=text + " extra", word_count=271),
        FetchedPage(url="https://c.com", ok=True, text="completely different content here " * 30, word_count=150),
    ]
    unique = dedupe_pages(pages)
    assert len(unique) == 2
