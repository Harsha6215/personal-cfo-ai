"""
Metrics Middleware — Sprint 6.5

On every request:
  - Increments request counter
  - Records latency
  - Tracks endpoint + status code
  - Tracks active user (if authenticated)

Completely non-blocking: if Redis is down, the request still proceeds.
"""

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.services.metrics import (
    inc_error_count,
    inc_request_count,
    record_latency,
    track_active_user,
)

logger = structlog.get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        method = request.method
        path = request.url.path

        # Fire-and-forget metrics (all fail-open)
        try:
            await inc_request_count(method, path)
            await record_latency(method, path, latency_ms)

            if response.status_code >= 400:
                await inc_error_count(response.status_code)

            # Track active user if authenticated
            user_id = _extract_user_id(request)
            if user_id:
                await track_active_user(user_id)
        except Exception as e:
            logger.debug("metrics_middleware.error", error=str(e))

        return response


def _extract_user_id(request: Request) -> str | None:
    """Try to get user_id from request state (set by auth middleware or route)."""
    # The auth dependency sets request.state.user after authentication
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return user.id

    # Fallback: check if request_id middleware set user context
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer ") and len(auth_header) > 10:
        # We don't decode the token here to avoid overhead on every request.
        # Active user tracking will be picked up by the auth dependency usage.
        return None
    return None
