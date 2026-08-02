"""
Redis-based sliding window rate limiter.

Uses a Redis sorted set (ZSET) per user to track request timestamps.
Requests older than the window are automatically pruned.

Default: 100 requests per 60 seconds per authenticated user.
Returns HTTP 429 when exceeded.
"""

import time

import structlog
from fastapi import Depends, HTTPException, Request, status

from backend.core.auth import get_current_user
from backend.models.user import User

logger = structlog.get_logger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
RATE_LIMIT_REQUESTS = 100  # max requests
RATE_LIMIT_WINDOW_SECONDS = 60  # per this many seconds


async def _get_redis():
    """Lazy import redis connection to avoid circular imports."""
    from backend.core.cache import get_redis_pool
    return await get_redis_pool()


async def check_rate_limit(
    request: Request,
    user: User = Depends(get_current_user),
) -> User:
    """
    Sliding window rate limiter using Redis ZSET.

    Key: rate_limit:{user_id}
    Members: request timestamps (score = timestamp)

    On each request:
    1. Remove entries older than window
    2. Count remaining entries
    3. If count >= limit, reject with 429
    4. Otherwise, add current timestamp

    Returns the user object so it can replace get_current_user in dependency chains.
    """
    try:
        redis = await _get_redis()
        if redis is None:
            # Redis unavailable — fail open (allow request)
            logger.warning("rate_limit.redis_unavailable", user_id=user.id)
            return user

        key = f"rate_limit:{user.id}"
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS

        pipe = redis.pipeline()
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Count current entries
        pipe.zcard(key)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Set TTL on key to auto-cleanup
        pipe.expire(key, RATE_LIMIT_WINDOW_SECONDS + 10)

        results = await pipe.execute()
        request_count = results[1]  # zcard result

        if request_count >= RATE_LIMIT_REQUESTS:
            logger.warning(
                "rate_limit.exceeded",
                user_id=user.id,
                count=request_count,
                limit=RATE_LIMIT_REQUESTS,
                endpoint=request.url.path,
            )
            # Remove the entry we just added since we're rejecting
            await redis.zrem(key, str(now))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS} seconds.",
                headers={"Retry-After": str(RATE_LIMIT_WINDOW_SECONDS)},
            )

    except HTTPException:
        raise
    except Exception as e:
        # Fail open — don't block users if Redis has issues
        logger.error("rate_limit.error", error=str(e), user_id=user.id)

    return user
