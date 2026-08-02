"""
Tenant isolation dependency.

Sets the PostgreSQL session variable `app.current_user_id` so that
Row-Level Security (RLS) policies can enforce data isolation at the
database level — defense-in-depth on top of application-layer filtering.

Usage in routes:
    from backend.core.tenant import get_tenant_db

    @router.get("/items")
    async def list_items(db: AsyncSession = Depends(get_tenant_db)):
        # RLS automatically filters rows to current user
        ...
"""

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.user import User


async def get_tenant_db(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AsyncSession:
    """
    Set PostgreSQL session variable for RLS enforcement.

    This sets `app.current_user_id` to the authenticated user's ID.
    RLS policies on tenant-scoped tables use:
        USING (user_id = current_setting('app.current_user_id')::text)

    The SET LOCAL scope ensures the variable is only valid for the
    current transaction, providing automatic cleanup.
    """
    await db.execute(
        text("SET LOCAL app.current_user_id = :user_id"),
        {"user_id": user.id},
    )
    return db
