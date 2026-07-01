from app.models import ResearchMode
from app.research.modes import get_mode
from app.research.rank import build_excerpt, rank_pages


def test_rank_assigns_ids_and_orders(sample_pages):
    mode = get_mode(ResearchMode.quick)
    sources = rank_pages("python programming language", sample_pages, mode)
    assert sources
    assert [s.id for s in sources] == list(range(1, len(sources) + 1))
    # Wikipedia (high trust + fresh + long) should rank first.
    assert sources[0].domain == "en.wikipedia.org"
    assert sources[0].scores.overall >= sources[-1].scores.overall


def test_rank_respects_max_sources(sample_pages):
    mode = get_mode(ResearchMode.quick)
    sources = rank_pages("python", sample_pages * 5, mode)
    assert len(sources) <= mode.max_sources


def test_build_excerpt_prefers_relevant_paragraphs():
    text = (
        "Unrelated intro paragraph about cooking.\n\n"
        "Python is a programming language used for data science and web development.\n\n"
        "Another unrelated paragraph about gardening."
    )
    excerpt = build_excerpt("python programming", text, max_words=40)
    assert "programming language" in excerpt


def test_rank_skips_empty_pages(sample_pages):
    from app.fetch.fetcher import FetchedPage

    pages = sample_pages + [FetchedPage(url="https://x.com", ok=False, text="")]
    mode = get_mode(ResearchMode.quick)
    sources = rank_pages("python", pages, mode)
    assert all(s.url != "https://x.com" for s in sources)


def _page(domain: str, n: int):
    from app.fetch.fetcher import FetchedPage

    text = f"{domain} article {n}. python programming language details. " * 30
    return FetchedPage(
        url=f"https://{domain}/{n}", ok=True, status=200, title=f"{domain} {n}",
        domain=domain, text=text, word_count=len(text.split()),
    )


def test_ranking_prefers_domain_diversity():
    # More candidates than slots (5 + 2, keep 4): diversity caps the dominant domain.
    pages = [_page("aaa.com", i) for i in range(5)] + [_page("bbb.com", i) for i in range(2)]
    sources = rank_pages("python programming", pages, get_mode(ResearchMode.quick))
    domains = [s.domain for s in sources]
    assert "bbb.com" in domains, "diverse domain should be included"
    assert domains.count("aaa.com") <= 2, "one domain should not dominate"


def test_ranking_backfills_single_domain():
    # All same domain: diversity must not starve the result — backfill fills it.
    pages = [_page("only.com", i) for i in range(5)]
    sources = rank_pages("python programming", pages, get_mode(ResearchMode.quick))
    assert len(sources) == get_mode(ResearchMode.quick).max_sources
