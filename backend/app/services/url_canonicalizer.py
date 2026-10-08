from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = {"gclid", "fbclid", "mc_cid", "mc_eid", "ref", "source"}


def _is_tracking(key: str) -> bool:
    lowered = key.lower()
    return lowered.startswith("utm_") or lowered in TRACKING_PARAMS


def canonicalize(url: str) -> str:
    """Normalize a URL for dedupe: lowercase host, drop tracking/fragment, sort query."""
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = parts.hostname or ""
    default_port = (scheme == "http" and parts.port == 80) or (
        scheme == "https" and parts.port == 443
    )
    netloc = host if parts.port is None or default_port else f"{host}:{parts.port}"
    path = parts.path.rstrip("/") if parts.path != "/" else "/"
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not _is_tracking(key)
        )
    )
    return urlunsplit((scheme, netloc, path, query, ""))
