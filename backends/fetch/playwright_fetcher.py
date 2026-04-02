"""
JS-rendered page fetcher using Playwright (optional).
Install: pip install playwright && playwright install chromium
Use js_render=true in /fetch endpoint to activate.
"""
try:
    from playwright.async_api import async_playwright
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

from bs4 import BeautifulSoup

async def fetch(url: str, max_chars: int = 8000) -> dict:
    if not AVAILABLE:
        raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install chromium")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=20000)
        html = await page.content()
        await browser.close()
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script","style","nav","footer"]): tag.decompose()
    lines = [l for l in soup.get_text(separator="\n", strip=True).splitlines() if l.strip()]
    text = "\n".join(lines)[:max_chars]
    return {"url": url, "status": 200, "title": soup.title.string if soup.title else None,
            "text": text, "char_count": len(text), "renderer": "playwright"}
