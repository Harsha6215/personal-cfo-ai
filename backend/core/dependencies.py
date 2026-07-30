"""
Shared FastAPI dependencies.

All reusable Depends() callables live here so route handlers stay clean.
Add more dependencies as needed (e.g. get_current_user in Story 6).

Usage:
    from backend.core.dependencies import get_db, get_settings

    async def my_route(
        db: AsyncSession = Depends(get_db),
        settings: Settings = Depends(get_settings),
    ):
        ...
"""

# Re-export so routes only need to import from one place
from backend.core.config import get_settings as get_settings  # noqa: F401
from backend.core.database import get_db as get_db  # noqa: F401
