from abc import ABC, abstractmethod
from typing import Any, Optional
import json
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseCache(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, expire_seconds: int = 3600) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass


class InMemoryCache(BaseCache):
    def __init__(self) -> None:
        self._cache: dict[str, tuple[Any, float]] = {}
        logger.info("Initialized local in-memory cache fallback.")

    async def get(self, key: str) -> Optional[Any]:
        import time
        if key not in self._cache:
            return None
        value, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None
        return value

    async def set(self, key: str, value: Any, expire_seconds: int = 3600) -> None:
        import time
        self._cache[key] = (value, time.time() + expire_seconds)

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)


class RedisCache(BaseCache):
    def __init__(self) -> None:
        self.redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("Initialized Redis Cache Client.")

    async def get(self, key: str) -> Optional[Any]:
        try:
            data = await self.redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Redis Cache GET failure: {e}")
        return None

    async def set(self, key: str, value: Any, expire_seconds: int = 3600) -> None:
        try:
            serialized = json.dumps(value)
            await self.redis_client.set(key, serialized, ex=expire_seconds)
        except Exception as e:
            logger.error(f"Redis Cache SET failure: {e}")

    async def delete(self, key: str) -> None:
        try:
            await self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Redis Cache DELETE failure: {e}")


# Single global instance provider
def get_cache() -> BaseCache:
    if settings.ENABLE_REDIS:
        try:
            return RedisCache()
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}. Falling back to InMemoryCache.")
            return InMemoryCache()
    return InMemoryCache()


cache = get_cache()
