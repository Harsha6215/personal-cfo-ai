"""
Redis connection pool — shared across the application.

Provides an async Redis client using the redis-py async API.
Falls back gracefully if Redis is unavailable (returns None).

Usage:
    from backend.core.cache import get_redis_pool

    redis = await get_redis_pool()
    if redis:
        await redis.set("key", "value")
"""

import structlog
from redis.asyncio import Redis, from_url

from backend.core.config import settings

logger = structlog.get_logger(__name__)

# Module-level singleton
_redis_pool: Redis | None = None
_connection_attempted: bool = False


async def get_redis_pool() -> Redis | None:
    """
    Get or create the Redis connection pool.
    Returns None if Redis is unavailable (fail-open pattern).
    """
    global _redis_pool, _connection_attempted

    if _redis_pool is not None:
        return _redis_pool

    if _connection_attempted:
        # Already tried and failed — don't retry every request
        return None

    _connection_attempted = True

    try:
        _redis_pool = from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
        )
        # Test connectivity
        await _redis_pool.ping()
        logger.info("redis.connected", url=settings.REDIS_URL.split("@")[-1])  # log without password
        return _redis_pool
    except Exception as e:
        logger.warning("redis.connection_failed", error=str(e))
        _redis_pool = None
        return None


async def close_redis_pool() -> None:
    """Close the Redis connection pool on application shutdown."""
    global _redis_pool, _connection_attempted
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None
    _connection_attempted = False
