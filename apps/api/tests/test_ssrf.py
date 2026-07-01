import pytest

from app.security.ssrf import UnsafeURLError, is_safe_url, validate_url


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/admin",
        "http://127.0.0.1:8000/",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "https://foo.local/",
        "ftp://example.com/file",
        "file:///etc/passwd",
    ],
)
def test_blocks_unsafe_urls(url):
    assert not is_safe_url(url)
    with pytest.raises(UnsafeURLError):
        validate_url(url)


def test_allows_public_https():
    assert validate_url("https://en.wikipedia.org/wiki/Python").startswith("https://")


def test_requires_host():
    with pytest.raises(UnsafeURLError):
        validate_url("https://")
