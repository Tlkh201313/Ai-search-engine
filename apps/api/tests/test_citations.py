from app.models import Source
from app.research.citations import apply_citations, extract_ids, sanitize


def _sources(n: int) -> list[Source]:
    return [Source(id=i, url=f"https://s{i}.com", title=f"S{i}") for i in range(1, n + 1)]


def test_extract_ids_handles_grouped_citations():
    assert extract_ids("a [1] b [2][3] c [4, 5]") == [1, 2, 3, 4, 5]


def test_sanitize_removes_out_of_range():
    text = "valid [1] and invalid [9] and grouped [2][9]"
    cleaned = sanitize(text, {1, 2, 3})
    assert "[9]" not in cleaned
    assert "[1]" in cleaned and "[2]" in cleaned


def test_apply_citations_marks_used():
    sources = _sources(3)
    used = apply_citations(["answer references [1] and [3]"], sources)
    assert used == [1, 3]
    assert sources[0].used and sources[2].used
    assert not sources[1].used


def test_apply_citations_ignores_invalid():
    sources = _sources(2)
    used = apply_citations(["cites [5] which does not exist"], sources)
    assert used == []
    assert not any(s.used for s in sources)
