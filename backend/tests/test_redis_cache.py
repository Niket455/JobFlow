from datetime import UTC, datetime

from fake_fetcher import FakeRedis

from app.core.redis_cache import DailyQuota, RedisCache


def test_cache_round_trip() -> None:
    cache = RedisCache(FakeRedis())
    assert cache.get("k") is None
    cache.setex("k", 60, "v")
    assert cache.get("k") == "v"


def test_cache_fails_open_on_redis_error() -> None:
    cache = RedisCache(FakeRedis(fail=True))
    assert cache.get("k") is None
    cache.setex("k", 60, "v")


def test_quota_allows_up_to_limit_then_refuses() -> None:
    quota = DailyQuota(FakeRedis())
    now = datetime(2026, 1, 1, 10, tzinfo=UTC)
    assert quota.try_consume("google_pse", 2, now=now) is True
    assert quota.try_consume("google_pse", 2, now=now) is True
    assert quota.try_consume("google_pse", 2, now=now) is False


def test_quota_fails_closed_on_redis_error() -> None:
    quota = DailyQuota(FakeRedis(fail=True))
    assert quota.try_consume("google_pse", 2, now=datetime(2026, 1, 1, tzinfo=UTC)) is False
