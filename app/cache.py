import json
from typing import Protocol

from app.config import get_settings


class Cache(Protocol):
    def get(self, key: str) -> dict | None: ...
    def set(self, key: str, value: dict) -> None: ...
    def delete(self, key: str) -> None: ...
    def clear(self) -> None: ...


class MemoryCache:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def get(self, key: str) -> dict | None:
        raw = self._values.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def set(self, key: str, value: dict) -> None:
        self._values[key] = json.dumps(value)

    def delete(self, key: str) -> None:
        self._values.pop(key, None)

    def clear(self) -> None:
        self._values.clear()


class RedisCache:
    def __init__(self, url: str) -> None:
        import redis

        self._redis = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> dict | None:
        raw = self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def set(self, key: str, value: dict) -> None:
        self._redis.set(key, json.dumps(value))

    def delete(self, key: str) -> None:
        self._redis.delete(key)

    def clear(self) -> None:
        self._redis.flushdb()


def build_cache() -> Cache:
    url = get_settings().redis_url.strip()
    if not url:
        return MemoryCache()
    return RedisCache(url)


cache: Cache = build_cache()
