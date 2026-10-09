import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlencode, urlsplit

import httpx

from app.adapters.base import FetchError
from app.adapters.http_json import get_json
from app.adapters.mapping import as_text
from app.adapters.robots import RobotsCache
from app.core.config import Settings, settings
from app.core.redis_cache import DailyQuota, RedisCache

PSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
ATOM = "{http://www.w3.org/2005/Atom}"


@dataclass
class DiscoveredLead:
    """A single candidate link surfaced by a discovery source (not yet fetched)."""

    title: str
    url: str
    domain: str | None
    source: str
    rough_score: float | None = None


class QuotaExceededError(FetchError):
    """Raised when a discovery source's daily quota is exhausted."""

    def __init__(self, url: str) -> None:
        super().__init__(url, "daily quota exhausted")


class DiscoverySource(Protocol):
    """A listing source: one feed/query yields many candidate leads."""

    kind: str

    def discover(self, target: str) -> list[DiscoveredLead]: ...


class RssDiscoverySource:
    """Parse an RSS 2.0 or Atom feed into candidate leads."""

    kind = "rss"

    def __init__(self, client: httpx.Client, robots: RobotsCache, *, user_agent: str) -> None:
        self._client = client
        self._robots = robots
        self._user_agent = user_agent

    def discover(self, target: str) -> list[DiscoveredLead]:
        if not self._robots.allowed(target, self._user_agent):
            raise FetchError(target, "robots.txt disallows fetching this URL")
        try:
            response = self._client.get(target)
        except httpx.HTTPError as exc:
            raise FetchError(target, str(exc)) from exc
        if response.status_code >= 400:
            raise FetchError(
                target, f"HTTP {response.status_code}", status_code=response.status_code
            )
        return _parse_feed(response.text, url=target, source=self.kind)


class GooglePseDiscoverySource:
    """Query a Google Programmable Search Engine, guarded by a daily quota + TTL cache."""

    kind = "google_pse"

    def __init__(
        self,
        client: httpx.Client,
        *,
        api_key: str | None,
        cx: str | None,
        cache: RedisCache,
        quota: DailyQuota,
        daily_quota: int,
        cache_seconds: int,
        num: int = 10,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._cx = cx
        self._cache = cache
        self._quota = quota
        self._daily_quota = daily_quota
        self._cache_seconds = cache_seconds
        self._num = num

    def discover(self, target: str) -> list[DiscoveredLead]:
        if not self._api_key or not self._cx:
            raise FetchError(target, "Google PSE is not configured")
        cache_key = f"pse:{self._cx}:{target}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return _pse_leads(json.loads(cached), source=self.kind)
        if not self._quota.try_consume("google_pse", self._daily_quota, now=datetime.now(UTC)):
            raise QuotaExceededError(target)
        params = urlencode({"key": self._api_key, "cx": self._cx, "q": target, "num": self._num})
        data = get_json(self._client, f"{PSE_ENDPOINT}?{params}")
        items = _pse_items(data)
        self._cache.setex(cache_key, self._cache_seconds, json.dumps(items))
        return _pse_leads(items, source=self.kind)


def build_discovery_source(
    kind: str,
    *,
    client: httpx.Client,
    robots: RobotsCache,
    cache: RedisCache,
    quota: DailyQuota,
    config: Settings = settings,
) -> DiscoverySource:
    if kind == "rss":
        return RssDiscoverySource(client, robots, user_agent=config.user_agent)
    if kind == "google_pse":
        return GooglePseDiscoverySource(
            client,
            api_key=config.google_pse_api_key,
            cx=config.google_pse_cx,
            cache=cache,
            quota=quota,
            daily_quota=config.google_pse_daily_quota,
            cache_seconds=config.google_pse_cache_seconds,
        )
    raise ValueError(f"unknown discovery kind: {kind}")


def _parse_feed(text: str, *, url: str, source: str) -> list[DiscoveredLead]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise FetchError(url, "feed was not valid XML") from exc
    if root.tag == "rss":
        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else []
        return _leads_from(items, _rss_item, source=source)
    if root.tag == ATOM + "feed":
        return _leads_from(root.findall(ATOM + "entry"), _atom_item, source=source)
    raise FetchError(url, "unsupported feed format")


def _leads_from(items: list[ET.Element], extract: Any, *, source: str) -> list[DiscoveredLead]:
    leads: list[DiscoveredLead] = []
    for item in items:
        title, url = extract(item)
        if not title or not url:
            continue
        domain = urlsplit(url).hostname
        if not domain:
            continue
        leads.append(DiscoveredLead(title=title, url=url, domain=domain, source=source))
    return leads


def _rss_item(item: ET.Element) -> tuple[str | None, str | None]:
    return as_text(item.findtext("title")), as_text(item.findtext("link"))


def _atom_item(entry: ET.Element) -> tuple[str | None, str | None]:
    title = as_text(entry.findtext(ATOM + "title"))
    link: str | None = None
    for candidate in entry.findall(ATOM + "link"):
        rel = candidate.get("rel")
        if rel in (None, "alternate") and candidate.get("href"):
            link = candidate.get("href")
            break
    return title, link


def _pse_items(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    items = data.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _pse_leads(items: list[dict[str, Any]], *, source: str) -> list[DiscoveredLead]:
    leads: list[DiscoveredLead] = []
    for item in items:
        title = as_text(item.get("title"))
        url = as_text(item.get("link"))
        if not title or not url:
            continue
        domain = urlsplit(url).hostname
        if not domain:
            continue
        leads.append(DiscoveredLead(title=title, url=url, domain=domain, source=source))
    return leads
