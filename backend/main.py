"""
Personal CFO AI — Backend
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.logging import setup_logging

# ── Setup ──────────────────────────────────────────────────────────────────────
setup_logging()

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Personal CFO AI",
    description="Enterprise-grade personal finance AI platform.",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Middleware ─────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "backend"}


@app.get("/version", tags=["System"])
async def version():
    """Returns the current application version."""
    return {"version": settings.APP_VERSION, "env": settings.APP_ENV}
