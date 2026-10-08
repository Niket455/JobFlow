import httpx

from app.adapters.base import FetchError, FetchResult, RobotsDisallowedError
from app.adapters.robots import RobotsCache
from app.core.config import settings


class HttpxFetcher:
    """Generic HTML fetcher for user-supplied URLs, honoring robots.txt."""

    def __init__(self, *, client: httpx.Client, user_agent: str, robots: RobotsCache) -> None:
        self._client = client
        self._user_agent = user_agent
        self._robots = robots

    def fetch(self, url: str) -> FetchResult:
        if not self._robots.allowed(url, self._user_agent):
            raise RobotsDisallowedError(url)
        try:
            response = self._client.get(url)
        except httpx.HTTPError as exc:
            raise FetchError(url, str(exc)) from exc
        if response.status_code >= 400:
            raise FetchError(url, f"HTTP {response.status_code}", status_code=response.status_code)
        return FetchResult(
            url=str(response.url),
            status_code=response.status_code,
            text=response.text,
            headers={key.lower(): value for key, value in response.headers.items()},
        )


def build_fetcher() -> HttpxFetcher:
    client = httpx.Client(
        timeout=settings.fetch_timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": settings.user_agent},
    )
    robots = RobotsCache(client, ttl_seconds=settings.robots_cache_ttl_seconds)
    return HttpxFetcher(client=client, user_agent=settings.user_agent, robots=robots)
