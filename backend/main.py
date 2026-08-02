"""
Personal CFO AI — Backend
FastAPI application entry point.

Startup order:
  1. Logging configured
  2. App created with OpenAPI metadata
  3. Middleware registered (order matters — outermost first)
  4. v1 API router mounted
  5. Root-level health + version kept for Docker healthchecks

Open http://localhost:8000/docs to see the full API documentation.
"""

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1.router import router as v1_router
from backend.core.config import settings
from backend.core.exceptions import AppError, app_error_handler, unhandled_error_handler
from backend.core.logging import setup_logging
from backend.middleware.logging import AccessLogMiddleware
from backend.middleware.rate_limit import RateLimitMiddleware
from backend.middleware.request_id import RequestIDMiddleware

# ── 1. Logging ─────────────────────────────────────────────────────────────────
setup_logging(log_level=settings.LOG_LEVEL, json_logs=settings.LOG_JSON)
logger = structlog.get_logger(__name__)

# ── 2. App ─────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Harshavardhan Reddy",
        "url": "https://github.com/Harsha6215/personal-cfo-ai",
    },
    license_info={"name": "MIT"},
    openapi_tags=[
        {"name": "System", "description": "Health checks and version info."},
        {"name": "Auth", "description": "Registration, login, JWT tokens. (Story 6)"},
        {"name": "Portfolio", "description": "Portfolio management. (Story 5+)"},
    ],
)

# ── 3. Middleware (outermost → innermost) ──────────────────────────────────────
# RequestID must be first so every log line downstream includes the request_id
app.add_middleware(RequestIDMiddleware)
app.add_middleware(AccessLogMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 4. Exception handlers ──────────────────────────────────────────────────────
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

# ── 5. Routers ─────────────────────────────────────────────────────────────────
app.include_router(v1_router)

# ── 6. Root-level shortcuts (kept for Docker HEALTHCHECK curl commands) ─────────
@app.get("/health", tags=["System"], include_in_schema=False)
async def health_root():
    return {"status": "ok", "service": "backend"}


@app.get("/version", tags=["System"], include_in_schema=False)
async def version_root():
    return {"version": settings.APP_VERSION, "env": settings.APP_ENV}


# ── 7. Startup / shutdown events ───────────────────────────────────────────────
@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "app.startup",
        name=settings.APP_NAME,
        version=settings.APP_VERSION,
        env=settings.APP_ENV,
        docs="http://localhost:8000/docs",
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    from backend.core.cache import close_redis_pool

    await close_redis_pool()
    logger.info("app.shutdown")
