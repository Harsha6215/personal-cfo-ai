"""
Rate limiting middleware.

Applies per-user rate limiting to all authenticated API endpoints.
Unauthenticated endpoints (login, register, health) are rate-limited by IP.

Uses the sliding window algorithm from backend.core.rate_limit.

Integration: Added to middleware stack in main.py.
"""

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = structlog.get_logger(__name__)

# Paths exempt from rate limiting
EXEMPT_PATHS = {
    "/health",
    "/version",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# Rate limits
AUTHENTICATED_LIMIT = 100  # per minute
UNAUTHENTICATED_LIMIT = 30  # per minute (by IP)
WINDOW_SECONDS = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces rate limits:
    - Authenticated users: 100 req/min (keyed by user_id from JWT)
    - Unauthenticated: 30 req/min (keyed by client IP)

    Fail-open: if Redis is unavailable, requests pass through.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip rate limiting for exempt paths
        path = request.url.path
        if path in EXEMPT_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        # Skip non-API paths (static assets, etc.)
        if not path.startswith("/api/"):
            return await call_next(request)

        try:
            from backend.core.cache import get_redis_pool

            redis = await get_redis_pool()
            if redis is None:
                # Fail open
                return await call_next(request)

            # Determine rate limit key
            # Try to extract user_id from Authorization header (lightweight, no DB hit)
            rate_key, limit = self._get_rate_key(request)

            now = time.time()
            window_start = now - WINDOW_SECONDS

            pipe = redis.pipeline()
            pipe.zremrangebyscore(rate_key, 0, window_start)
            pipe.zcard(rate_key)
            pipe.zadd(rate_key, {str(now): now})
            pipe.expire(rate_key, WINDOW_SECONDS + 10)

            results = await pipe.execute()
            request_count = results[1]

            if request_count >= limit:
                logger.warning(
                    "rate_limit.middleware.exceeded",
                    key=rate_key,
                    count=request_count,
                    limit=limit,
                    path=path,
                )
                # Remove the entry we just added
                await redis.zrem(rate_key, str(now))
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"Rate limit exceeded. Max {limit} requests per {WINDOW_SECONDS} seconds."
                    },
                    headers={"Retry-After": str(WINDOW_SECONDS)},
                )

        except Exception as e:
            # Fail open on any error
            logger.error("rate_limit.middleware.error", error=str(e))

        return await call_next(request)

    def _get_rate_key(self, request: Request) -> tuple[str, int]:
        """
        Determine the rate limit key and limit.
        If authenticated (has Bearer token), use user-based key.
        Otherwise, use IP-based key.
        """
        auth_header = request.headers.get("authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # Decode just the sub claim without DB lookup (lightweight)
            try:
                from backend.core.security import decode_token

                payload = decode_token(token)
                if payload and payload.get("sub"):
                    return f"rate_limit:user:{payload['sub']}", AUTHENTICATED_LIMIT
            except Exception:
                pass

        # Fallback to IP-based limiting
        client_ip = request.client.host if request.client else "unknown"
        return f"rate_limit:ip:{client_ip}", UNAUTHENTICATED_LIMIT
