from __future__ import annotations

import urllib.parse

LOCAL_HTTP_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def require_local_http_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in LOCAL_HTTP_HOSTS:
        raise ValueError("runtime transport URL must be a local HTTP URL")
    if parsed.username or parsed.password:
        raise ValueError("runtime transport URL must be a local HTTP URL without credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("runtime transport URL must not include query or fragment")
    return url
