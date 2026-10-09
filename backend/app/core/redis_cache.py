import logging
from datetime import UTC, datetime, time, timedelta

import redis

logger = logging.getLogger(__name__)


class RedisCache:
    """A best-effort TTL cache. Any Redis error degrades to a cache miss (fail-open)."""

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    def get(self, key: str) -> str | None:
        try:
            value = self._client.get(key)
        except redis.RedisError:
            return None
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else str(value)

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        try:
            self._client.setex(key, ttl_seconds, value)
        except redis.RedisError:
            logger.warning("redis cache set failed for key %s", key)


class DailyQuota:
    """A per-day counter. Fails closed: if Redis is unreachable the call is refused."""

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    def try_consume(self, name: str, limit: int, *, now: datetime) -> bool:
        key = f"quota:{name}:{now.astimezone(UTC).date().isoformat()}"
        try:
            used = int(self._client.incr(key))
            if used == 1:
                self._client.expire(key, _seconds_until_end_of_day(now))
        except redis.RedisError:
            return False
        return used <= limit


def _seconds_until_end_of_day(now: datetime) -> int:
    moment = now.astimezone(UTC)
    tomorrow = datetime.combine(moment.date() + timedelta(days=1), time.min, tzinfo=UTC)
    return max(1, int((tomorrow - moment).total_seconds()))
