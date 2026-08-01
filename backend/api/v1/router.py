"""
API v1 router.

All v1 route modules are registered here and mounted at /api/v1 in main.py.
As new features are added (auth, portfolio, etc.), import and include them here.

Example:
    from backend.api.v1 import auth, portfolio
    router.include_router(auth.router, prefix="/auth")
    router.include_router(portfolio.router, prefix="/portfolios")
"""

from fastapi import APIRouter

from backend.api.v1 import system

router = APIRouter(prefix="/api/v1")

# ── System ─────────────────────────────────────────────────────────────────────
router.include_router(system.router)

# ── Story 6: Auth ──────────────────────────────────────────────────────────────
from backend.api.v1 import auth
router.include_router(auth.router, prefix="/auth")

# ── Epic 2: Portfolio & Assets ─────────────────────────────────────────────────
from backend.api.v1 import portfolios, assets, imports, reconciliation
router.include_router(portfolios.router, prefix="/portfolios")
router.include_router(assets.router, prefix="/assets")
router.include_router(imports.router, prefix="/import")
router.include_router(reconciliation.router, prefix="/reconciliation")
