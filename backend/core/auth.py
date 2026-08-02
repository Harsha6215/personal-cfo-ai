"""
Authentication dependencies for FastAPI.

Provides:
    - get_current_user: extract + validate JWT, return User
    - require_admin: same as above but enforces UserRole.ADMIN

Usage in any route:
    from backend.core.auth import get_current_user, require_admin

    @router.get("/me")
    async def me(user: User = Depends(get_current_user)):
        return user

    @router.get("/admin/users")
    async def list_users(user: User = Depends(require_admin)):
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import decode_token
from backend.models.user import User, UserRole

# This tells Swagger to show a "lock" icon and send Bearer tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Decode the JWT, check blacklist, look up the user, and return it.
    Raises 401 if the token is invalid, blacklisted, or user doesn't exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    token_type: str | None = payload.get("type")
    jti: str | None = payload.get("jti")

    if user_id is None or token_type != "access":
        raise credentials_exception

    # Check token blacklist (logout invalidation)
    if jti:
        from backend.services.token_blacklist import is_token_blacklisted
        if await is_token_blacklisted(jti):
            raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    return user


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that enforces admin role.
    Use on admin-only endpoints.
    Raises 403 if user is not an admin.
    """
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return user
