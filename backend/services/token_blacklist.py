"""
Token blacklist service — Epic 6 Sprint 6.3

On logout, the token's JTI (JWT ID) is added to a Redis set with a TTL
matching the token's remaining lifetime. The `get_current_user` dependency
checks the blacklist before accepting a token.

Redis key pattern: token_blacklist:{jti}
TTL: remaining seconds until token expiration

Fail-open: if Redis is unavailable, tokens are still accepted (logged as warning).
"""

import time

import structlog

logger = structlog.get_logger(__name__)

BLACKLIST_PREFIX = "token_blacklist:"


async def _get_redis():
    """Lazy import to avoid circular imports."""
    try:
        from backend.core.cache import get_redis_pool
        return await get_redis_pool()
    except Exception:
        return None


async def blacklist_token(jti: str, exp: int) -> bool:
    """
    Add a token JTI to the blacklist.

    Args:
        jti: The JWT ID claim from the token.
        exp: The token's expiration timestamp (epoch seconds).

    Returns:
        True if blacklisted successfully, False otherwise.
    """
    redis = await _get_redis()
    if redis is None:
        logger.warning("token_blacklist.redis_unavailable", jti=jti)
        return False

    try:
        ttl = max(int(exp - time.time()), 1)
        key = f"{BLACKLIST_PREFIX}{jti}"
        await redis.setex(key, ttl, "1")
        logger.info("token_blacklist.added", jti=jti, ttl=ttl)
        return True
    except Exception as e:
        logger.error("token_blacklist.error", error=str(e), jti=jti)
        return False


async def is_token_blacklisted(jti: str) -> bool:
    """
    Check if a token JTI is blacklisted.

    Returns False (not blacklisted) if Redis is unavailable (fail-open).
    """
    redis = await _get_redis()
    if redis is None:
        return False

    try:
        key = f"{BLACKLIST_PREFIX}{jti}"
        result = await redis.exists(key)
        return bool(result)
    except Exception as e:
        logger.error("token_blacklist.check_error", error=str(e), jti=jti)
        return False  # Fail open
