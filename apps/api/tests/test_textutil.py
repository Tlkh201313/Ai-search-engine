from app.textutil import domain_of, jaccard, keywords, normalize_url, title_similarity


def test_normalize_url_strips_tracking_and_www():
    a = normalize_url("https://www.Example.com/path/?utm_source=x&id=5#frag")
    b = normalize_url("http://example.com/path?id=5")
    assert a == b
    assert "utm_source" not in a
    assert "#frag" not in a


def test_normalize_url_trailing_slash():
    assert normalize_url("https://python.org/") == normalize_url("https://python.org")


def test_domain_of():
    assert domain_of("https://www.bbc.co.uk/news") == "bbc.co.uk"
    assert domain_of("https://arxiv.org/abs/1234") == "arxiv.org"


def test_keywords_removes_stopwords():
    kw = keywords("What is the best way to learn Python")
    assert "python" in kw
    assert "the" not in kw and "is" not in kw


def test_jaccard_and_title_similarity():
    assert jaccard({"a", "b"}, {"a", "b"}) == 1.0
    assert jaccard({"a"}, {"b"}) == 0.0
    assert title_similarity("Hello World", "hello world") > 0.9
