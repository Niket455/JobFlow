import httpx

from app.adapters.ashby import AshbyAdapter
from app.adapters.base import Adapter, Fetcher
from app.adapters.dispatch import DispatchFetcher
from app.adapters.greenhouse import GreenhouseAdapter
from app.adapters.lever import LeverAdapter
from app.adapters.robots import RobotsCache
from app.adapters.user_url import HttpxFetcher
from app.core.config import settings


def build_fetcher(client: httpx.Client | None = None) -> Fetcher:
    """Build the ingestion fetcher.

    Returns an ATS-aware dispatcher (Greenhouse/Lever/Ashby public JSON APIs) that falls back to
    the generic HTML fetcher. When `enable_ats_ingestion` is off, only the HTML fetcher is used.
    `client` is injectable so tests can supply an offline transport.
    """
    if client is None:
        client = httpx.Client(
            timeout=settings.fetch_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": settings.user_agent},
        )
    robots = RobotsCache(client, ttl_seconds=settings.robots_cache_ttl_seconds)
    html = HttpxFetcher(client=client, user_agent=settings.user_agent, robots=robots)
    if not settings.enable_ats_ingestion:
        return html
    adapters: list[Adapter] = [
        GreenhouseAdapter(client),
        LeverAdapter(client),
        AshbyAdapter(client),
    ]
    return DispatchFetcher(adapters, html)
