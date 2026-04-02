"""
FUTURE: Rotate free/paid proxies so backends never see the same IP twice.
Plug in by wrapping httpx.AsyncClient with get_proxied_client().
"""
FREE_PROXY_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
]

async def fetch_free_proxies() -> list:
    import httpx
    proxies = []
    async with httpx.AsyncClient() as client:
        for url in FREE_PROXY_SOURCES:
            try:
                r = await client.get(url, timeout=10)
                proxies += [p.strip() for p in r.text.splitlines() if p.strip()]
            except Exception:
                continue
    return list(set(proxies))

# TODO: implement get_proxied_client() with health checking + rotation
