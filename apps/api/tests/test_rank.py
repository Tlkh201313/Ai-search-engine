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
