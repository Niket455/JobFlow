import pytest
from fake_fetcher import (
    ATOM_FEED_URL,
    DE_URL,
    PSE_QUERY,
    PSE_URL,
    RSS_FEED_URL,
    FakeRedis,
    discovery_client,
)

from app.adapters.discovery import (
    GooglePseDiscoverySource,
    QuotaExceededError,
    RssDiscoverySource,
    build_discovery_source,
)
from app.adapters.robots import RobotsCache
from app.core.config import settings
from app.core.redis_cache import DailyQuota, RedisCache


def _rss_source() -> RssDiscoverySource:
    client, _ = discovery_client()
    return RssDiscoverySource(
        client, RobotsCache(client, ttl_seconds=3600), user_agent=settings.user_agent
    )


def test_rss_source_parses_items() -> None:
    leads = _rss_source().discover(RSS_FEED_URL)
    assert [lead.title for lead in leads] == ["Data Engineer", "Ghost Role"]
    assert leads[0].url == DE_URL
    assert leads[0].domain == "jobs.example.com"
    assert all(lead.source == "rss" for lead in leads)


def test_atom_source_parses_entries() -> None:
    leads = _rss_source().discover(ATOM_FEED_URL)
    assert len(leads) == 1
    assert leads[0].title == "Site Reliability Engineer"
    assert leads[0].url == "https://atom.example.com/sre"
    assert leads[0].domain == "atom.example.com"


def test_pse_source_parses_and_caches() -> None:
    client, calls = discovery_client()
    source = GooglePseDiscoverySource(
        client,
        api_key="test-key",
        cx="test-cx",
        cache=RedisCache(FakeRedis()),
        quota=DailyQuota(FakeRedis()),
        daily_quota=100,
        cache_seconds=86400,
    )
    first = source.discover(PSE_QUERY)
    second = source.discover(PSE_QUERY)

    assert [lead.title for lead in first] == ["Python Developer", "Data Engineer"]
    assert second == first
    assert calls.count(PSE_URL) == 1


def test_pse_quota_guard_short_circuits() -> None:
    client, _ = discovery_client()
    source = GooglePseDiscoverySource(
        client,
        api_key="k",
        cx="c",
        cache=RedisCache(FakeRedis()),
        quota=DailyQuota(FakeRedis()),
        daily_quota=1,
        cache_seconds=86400,
    )
    source.discover(PSE_QUERY)
    with pytest.raises(QuotaExceededError):
        source.discover("a different query")


def test_unknown_kind_raises() -> None:
    client, _ = discovery_client()
    with pytest.raises(ValueError):
        build_discovery_source(
            "chat",
            client=client,
            robots=RobotsCache(client, ttl_seconds=0),
            cache=RedisCache(FakeRedis()),
            quota=DailyQuota(FakeRedis()),
        )
