"""
Access Log Middleware.

Logs every HTTP request with:
  - method, path, status code, duration (ms)
  - request_id (injected by RequestIDMiddleware)

Example log line:
  2026-07-31T10:00:00Z [info] http.request method=GET path=/health status=200 duration_ms=3.2
"""

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response
