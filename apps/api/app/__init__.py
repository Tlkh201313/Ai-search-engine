"""AI Research Engine — FastAPI backend."""

__version__ = "1.0.0"


def _use_os_trust_store() -> None:
    """Verify TLS against the OS trust store (like browsers / curl) instead of
    only certifi's bundle.

    Some servers (and gateways) ship an incomplete certificate chain — missing an
    intermediate. The OS verifier fetches the missing intermediate automatically
    (AIA), which OpenSSL/certifi cannot, so those hosts fail in Python with
    "unable to get local issuer certificate" while succeeding in a browser. This
    routes verification through the platform verifier to fix that. It never
    weakens verification, and is a no-op if truststore isn't installed.
    """
    try:
        import truststore

        truststore.inject_into_ssl()
    except Exception:  # pragma: no cover - truststore optional / best effort
        pass


_use_os_trust_store()
