"""SSRF protection — validate outbound fetch URLs.

Blocks non-http(s) schemes and hosts that resolve to private, loopback,
link-local, or otherwise reserved IP ranges unless explicitly allowed
(``ALLOW_PRIVATE_IPS=true`` for local development).
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from app.config import settings


class UnsafeURLError(ValueError):
    """Raised when a URL fails SSRF validation."""


_BLOCKED_HOST_SUFFIXES = (".local", ".internal", ".localhost")
_ALLOWED_SCHEMES = {"http", "https"}


def _is_public_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_url(url: str) -> str:
    """Return a normalized URL or raise :class:`UnsafeURLError`."""
    parsed = urlparse(url.strip())

    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeURLError(f"unsupported scheme: {parsed.scheme!r}")

    host = parsed.hostname
    if not host:
        raise UnsafeURLError("missing host")

    if settings.allow_private_ips:
        return url.strip()

    lowered = host.lower()
    if lowered == "localhost" or lowered.endswith(_BLOCKED_HOST_SUFFIXES):
        raise UnsafeURLError(f"blocked host: {host}")

    # If the host is a literal IP, check it directly.
    try:
        ipaddress.ip_address(host)
        if not _is_public_ip(host):
            raise UnsafeURLError(f"blocked non-public IP: {host}")
        return url.strip()
    except ValueError:
        pass  # hostname, resolve below

    # Resolve the hostname; every resolved address must be public.
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"cannot resolve host: {host}") from exc

    for info in infos:
        ip_str = info[4][0]
        if not _is_public_ip(ip_str):
            raise UnsafeURLError(f"host resolves to non-public IP: {ip_str}")

    return url.strip()


def is_safe_url(url: str) -> bool:
    try:
        validate_url(url)
        return True
    except UnsafeURLError:
        return False
