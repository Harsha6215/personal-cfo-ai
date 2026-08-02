"""
Access Log Middleware — Sprint 6.5 enhanced.

Logs every HTTP request in structured JSON format including:
  - request_id (from RequestIDMiddleware contextvars)
  - user_id (extracted from Bearer token if present)
  - endpoint (method + path)
  - response_time_ms
  - status_code

Example log line (JSON mode):
  {"event":"http.request","request_id":"abc-123","user_id":"u-456",
   "method":"GET","path":"/api/v1/admin/metrics","status_code":200,
   "response_time_ms":12.5,"endpoint":"GET /api/v1/admin/metrics"}
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
        response_time_ms = round((time.perf_counter() - start) * 1000, 2)

        # Extract user_id from auth header (lightweight — no DB call)
        user_id = _extract_user_id_from_header(request)

        method = request.method
        path = request.url.path
        status_code = response.status_code

        logger.info(
            "http.request",
            method=method,
            path=path,
            status_code=status_code,
            response_time_ms=response_time_ms,
            endpoint=f"{method} {path}",
            user_id=user_id,
        )
        return response


def _extract_user_id_from_header(request: Request) -> str | None:
    """
    Attempt to extract user_id from JWT payload without full validation.
    Used only for logging — auth is handled by the route dependency.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]
    try:
        # Lightweight decode just for logging — ignores expiry
        import json
        import base64

        parts = token.split(".")
        if len(parts) != 3:
            return None
        # Decode payload (second part)
        payload_b64 = parts[1]
        # Add padding
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload.get("sub")
    except Exception:
        return None
