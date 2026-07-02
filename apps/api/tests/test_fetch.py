import httpx
import pytest
import respx

from app.fetch import fetcher
from app.fetch.fetcher import fetch_page
from app.security.ssrf import UnsafeURLError


def _fake_validate(url: str) -> str:
    """Validate like production but skip DNS: block private/metadata literals."""
    for bad in ("169.254.169.254", "127.0.0.1", "10.0.0.", "192.168.", "localhost"):
        if bad in url:
            raise UnsafeURLError(f"blocked: {bad}")
    return url


@pytest.mark.asyncio
@respx.mock
async def test_fetch_blocks_redirect_to_private_ip(monkeypatch):
    monkeypatch.setattr(fetcher, "validate_url", _fake_validate)
    # A public page that redirects to the cloud metadata endpoint.
    respx.get("https://safe.test/").mock(
        return_value=httpx.Response(302, headers={"location": "http://169.254.169.254/latest/"})
    )
    page = await fetch_page("https://safe.test/", use_cache=False)
    assert not page.ok
    assert "blocked redirect" in (page.error or "")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_follows_safe_redirect_and_extracts(monkeypatch):
    monkeypatch.setattr(fetcher, "validate_url", _fake_validate)
    respx.get("https://safe.test/").mock(
        return_value=httpx.Response(301, headers={"location": "https://safe.test/article"})
    )
    respx.get("https://safe.test/article").mock(
        return_value=httpx.Response(
            200,
            headers={"content-type": "text/html"},
            html="<html><head><title>Hi</title></head><body><article>"
            "<p>This is a sufficiently long readable paragraph of body content.</p>"
            "</article></body></html>",
        )
    )
    page = await fetch_page("https://safe.test/", use_cache=False)
    assert page.ok
    assert "readable paragraph" in page.text


@pytest.mark.asyncio
@respx.mock
async def test_fetch_rejects_non_html(monkeypatch):
    monkeypatch.setattr(fetcher, "validate_url", _fake_validate)
    respx.get("https://safe.test/file.pdf").mock(
        return_value=httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF")
    )
    page = await fetch_page("https://safe.test/file.pdf", use_cache=False)
    assert not page.ok
    assert "unsupported content-type" in (page.error or "")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_caps_download_size(monkeypatch):
    monkeypatch.setattr(fetcher, "validate_url", _fake_validate)
    monkeypatch.setattr(fetcher, "_MAX_BYTES", 1000)
    big = "<html><body><article>" + ("word " * 5000) + "</article></body></html>"
    respx.get("https://safe.test/big").mock(
        return_value=httpx.Response(200, headers={"content-type": "text/html"}, text=big)
    )
    page = await fetch_page("https://safe.test/big", use_cache=False)
    # Body read was capped, so far fewer bytes than the full document were processed.
    assert page.ok
    assert len(page.text) < len(big)
