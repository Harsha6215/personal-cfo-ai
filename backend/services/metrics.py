"""
Redis-based metrics collector — Sprint 6.5

Tracks:
  - request_count (total + per endpoint)
  - error_count (by status code)
  - latency_p50, latency_p95 (per endpoint)
  - llm_calls (per user/day)
  - active_users (daily)

Uses Redis INCR for counters, sorted sets for latency percentiles.
Fails open when Redis is unavailable — no metrics is acceptable, but
a broken app is not.
"""

import time
from datetime import date

import structlog

logger = structlog.get_logger(__name__)


async def _get_redis():
    """Lazy import to avoid module-level redis dependency."""
    try:
        from backend.core.cache import get_redis_pool
        return await _get_redis()
    except Exception:
        return None

# Redis key prefixes
_PREFIX = "metrics"
_REQ_TOTAL = f"{_PREFIX}:req:total"
_REQ_ENDPOINT = f"{_PREFIX}:req:endpoint"  # :{method}:{path}
_ERR_STATUS = f"{_PREFIX}:err:status"  # :{code}
_LATENCY = f"{_PREFIX}:latency"  # :{method}:{path}
_LLM_CALLS = f"{_PREFIX}:llm:calls"  # :{user_id}:{date}
_LLM_TOTAL = f"{_PREFIX}:llm:total"  # :{date}
_ACTIVE_USERS = f"{_PREFIX}:active_users"  # :{date}


def _today() -> str:
    return date.today().isoformat()


async def inc_request_count(method: str, path: str) -> None:
    """Increment total and per-endpoint request counters."""
    try:
        redis = await _get_redis()
        if not redis:
            return
        pipe = redis.pipeline()
        pipe.incr(_REQ_TOTAL)
        pipe.incr(f"{_REQ_ENDPOINT}:{method}:{path}")
        pipe.incr(f"{_REQ_TOTAL}:{_today()}")
        await pipe.execute()
    except Exception as e:
        logger.debug("metrics.inc_request_count.failed", error=str(e))


async def inc_error_count(status_code: int) -> None:
    """Increment error counter by status code."""
    try:
        redis = await _get_redis()
        if not redis:
            return
        await redis.incr(f"{_ERR_STATUS}:{status_code}")
        await redis.incr(f"{_ERR_STATUS}:{status_code}:{_today()}")
    except Exception as e:
        logger.debug("metrics.inc_error_count.failed", error=str(e))


async def record_latency(method: str, path: str, latency_ms: float) -> None:
    """Record latency for percentile calculation using sorted set (score=timestamp)."""
    try:
        redis = await _get_redis()
        if not redis:
            return
        key = f"{_LATENCY}:{method}:{path}"
        # Use a sorted set where score = latency_ms and member = timestamp for uniqueness
        member = f"{time.time_ns()}"
        await redis.zadd(key, {member: latency_ms})
        # Keep only last 1000 entries per endpoint to bound memory
        await redis.zremrangebyrank(key, 0, -1001)
        # Also record in global latency key
        global_key = f"{_LATENCY}:global"
        await redis.zadd(global_key, {member: latency_ms})
        await redis.zremrangebyrank(global_key, 0, -1001)
    except Exception as e:
        logger.debug("metrics.record_latency.failed", error=str(e))


async def track_active_user(user_id: str) -> None:
    """Track daily active user via a Redis set."""
    try:
        redis = await _get_redis()
        if not redis:
            return
        key = f"{_ACTIVE_USERS}:{_today()}"
        await redis.sadd(key, user_id)
        # Expire after 7 days to auto-cleanup
        await redis.expire(key, 7 * 86400)
    except Exception as e:
        logger.debug("metrics.track_active_user.failed", error=str(e))


async def inc_llm_calls(user_id: str) -> None:
    """Increment LLM call counter for a user/day."""
    try:
        redis = await _get_redis()
        if not redis:
            return
        today = _today()
        pipe = redis.pipeline()
        pipe.incr(f"{_LLM_CALLS}:{user_id}:{today}")
        pipe.incr(f"{_LLM_TOTAL}:{today}")
        pipe.expire(f"{_LLM_CALLS}:{user_id}:{today}", 30 * 86400)
        pipe.expire(f"{_LLM_TOTAL}:{today}", 30 * 86400)
        await pipe.execute()
    except Exception as e:
        logger.debug("metrics.inc_llm_calls.failed", error=str(e))


# ── Read helpers (for admin dashboard) ─────────────────────────────────────────


async def get_request_count_today() -> int:
    """Get total requests today."""
    try:
        redis = await _get_redis()
        if not redis:
            return 0
        val = await redis.get(f"{_REQ_TOTAL}:{_today()}")
        return int(val) if val else 0
    except Exception:
        return 0


async def get_error_count_today() -> int:
    """Sum all error counts (4xx + 5xx) for today."""
    try:
        redis = await _get_redis()
        if not redis:
            return 0
        total = 0
        for code in range(400, 600):
            val = await redis.get(f"{_ERR_STATUS}:{code}:{_today()}")
            if val:
                total += int(val)
        return total
    except Exception:
        return 0


async def get_latency_percentiles() -> dict:
    """Calculate p50 and p95 latency from global sorted set."""
    try:
        redis = await _get_redis()
        if not redis:
            return {"p50": 0, "p95": 0}
        key = f"{_LATENCY}:global"
        count = await redis.zcard(key)
        if count == 0:
            return {"p50": 0, "p95": 0}
        # Get all scores (latencies)
        members = await redis.zrangebyscore(key, "-inf", "+inf", withscores=True)
        latencies = sorted([score for _, score in members])
        n = len(latencies)
        p50 = latencies[int(n * 0.5)] if n > 0 else 0
        p95 = latencies[int(n * 0.95)] if n > 1 else latencies[-1] if n > 0 else 0
        return {"p50": round(p50, 2), "p95": round(p95, 2)}
    except Exception:
        return {"p50": 0, "p95": 0}


async def get_active_users_today() -> int:
    """Get count of active users today."""
    try:
        redis = await _get_redis()
        if not redis:
            return 0
        key = f"{_ACTIVE_USERS}:{_today()}"
        return await redis.scard(key)
    except Exception:
        return 0


async def get_llm_total_today() -> int:
    """Get total LLM calls today."""
    try:
        redis = await _get_redis()
        if not redis:
            return 0
        val = await redis.get(f"{_LLM_TOTAL}:{_today()}")
        return int(val) if val else 0
    except Exception:
        return 0
