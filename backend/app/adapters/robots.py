import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx


class RobotsCache:
    """Caches parsed robots.txt per origin and answers fetch-permission queries."""

    def __init__(self, client: httpx.Client, *, ttl_seconds: int) -> None:
        self._client = client
        self._ttl = ttl_seconds
        self._cache: dict[str, tuple[float, RobotFileParser | None]] = {}

    def allowed(self, url: str, user_agent: str) -> bool:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        parser = self._parser_for(f"{parsed.scheme}://{parsed.netloc}")
        if parser is None:
            return True
        return parser.can_fetch(user_agent, url)

    def _parser_for(self, origin: str) -> RobotFileParser | None:
        now = time.monotonic()
        cached = self._cache.get(origin)
        if cached is not None and cached[0] > now:
            return cached[1]
        parser = self._load(origin)
        self._cache[origin] = (now + self._ttl, parser)
        return parser

    def _load(self, origin: str) -> RobotFileParser | None:
        try:
            response = self._client.get(urljoin(origin, "/robots.txt"))
        except httpx.HTTPError:
            return None
        if response.status_code >= 400:
            return None
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        return parser
