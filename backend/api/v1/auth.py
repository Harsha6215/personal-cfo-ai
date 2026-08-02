"""
Authentication API routes — Epic 6 Sprint 6.3

Endpoints:
    POST /api/v1/auth/register    — create new user
    POST /api/v1/auth/login       — get access + refresh tokens
    POST /api/v1/auth/google      — Google OAuth login/register
    POST /api/v1/auth/request-otp — send OTP to email
    POST /api/v1/auth/verify-otp  — validate OTP, return tokens
    POST /api/v1/auth/refresh     — get new access token (rotation)
    POST /api/v1/auth/logout      — blacklist current token
    GET  /api/v1/auth/me          — get current user profile
    DELETE /api/v1/auth/account   — soft-delete account
"""

import secrets
import time

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from backend.models.user import User
from backend.schemas.user import UserResponse
from backend.services.token_blacklist import blacklist_token

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Auth"])


# ── Request/Response schemas ───────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    invite_code: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class GoogleAuthRequest(BaseModel):
    """Accepts either an authorization code or an ID token from Google."""
    code: str | None = None
    id_token: str | None = None


class OTPRequest(BaseModel):
    email: EmailStr


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    if len(body.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters.",
        )

    # Validate invite code if provided
    invite = None
    if body.invite_code:
        from datetime import datetime, timezone
        from backend.models.invite_code import InviteCode

        invite_result = await db.execute(
            select(InviteCode).where(InviteCode.code == body.invite_code)
        )
        invite = invite_result.scalar_one_or_none()

        if invite is None or not invite.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invite code",
            )
        if invite.current_uses >= invite.max_uses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invite code",
            )
        if invite.expires_at and invite.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invite code",
            )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    # Increment invite code usage on successful registration
    if invite:
        invite.current_uses += 1
        await db.flush()

    logger.info("auth.register", user_id=user.id, email=user.email)
    return user


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login with email and password",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    logger.info("auth.login", user_id=user.id, email=user.email)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


# ── Google OAuth ───────────────────────────────────────────────────────────────

@router.post(
    "/google",
    response_model=LoginResponse,
    summary="Login/Register with Google",
    description="Accepts a Google auth code or ID token. Creates user if new.",
)
async def google_auth(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    from backend.services.oauth import exchange_google_code, exchange_google_id_token
    from backend.core.config import settings

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    if not body.code and not body.id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'code' or 'id_token'.",
        )

    try:
        if body.id_token:
            google_user = await exchange_google_id_token(body.id_token)
        else:
            google_user = await exchange_google_code(body.code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    if not google_user.email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    # Find or create user
    result = await db.execute(select(User).where(User.email == google_user.email))
    user = result.scalar_one_or_none()

    if user is None:
        # Create new user (no password — OAuth-only)
        user = User(
            email=google_user.email,
            hashed_password="OAUTH_NO_PASSWORD",
            full_name=google_user.name,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        logger.info("auth.google.register", user_id=user.id, email=user.email)
    else:
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated.")
        logger.info("auth.google.login", user_id=user.id, email=user.email)

    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


# ── OTP Login ──────────────────────────────────────────────────────────────────

@router.post(
    "/request-otp",
    response_model=MessageResponse,
    summary="Request OTP for passwordless login",
    description="Sends a 6-digit OTP to the user's email (stored in Redis).",
)
async def request_otp(body: OTPRequest, db: AsyncSession = Depends(get_db)):
    from backend.core.config import settings

    # Verify user exists
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None:
        # Don't reveal if user exists — always say "sent"
        logger.info("auth.otp.request_nonexistent", email=body.email)
        return MessageResponse(message="If an account exists, an OTP has been sent.")

    # Generate 6-digit OTP
    otp = f"{secrets.randbelow(1000000):06d}"

    # Store in Redis with TTL
    try:
        from backend.core.cache import get_redis_pool
        redis = await get_redis_pool()
        if redis:
            key = f"otp:{body.email}"
            await redis.setex(key, settings.OTP_EXPIRE_MINUTES * 60, otp)
        else:
            logger.warning("auth.otp.redis_unavailable")
            raise HTTPException(status_code=503, detail="OTP service temporarily unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("auth.otp.store_error", error=str(e))
        raise HTTPException(status_code=503, detail="OTP service temporarily unavailable")

    # In production: send via email service (SendGrid, SES, etc.)
    # For development: log it
    logger.info("auth.otp.generated", email=body.email, otp=otp)

    return MessageResponse(message="If an account exists, an OTP has been sent.")


@router.post(
    "/verify-otp",
    response_model=LoginResponse,
    summary="Verify OTP and get tokens",
)
async def verify_otp(body: OTPVerifyRequest, db: AsyncSession = Depends(get_db)):
    # Validate OTP from Redis
    try:
        from backend.core.cache import get_redis_pool
        redis = await get_redis_pool()
        if redis is None:
            raise HTTPException(status_code=503, detail="OTP service temporarily unavailable")

        key = f"otp:{body.email}"
        stored_otp = await redis.get(key)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="OTP service temporarily unavailable")

    if stored_otp is None or stored_otp != body.otp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP.",
        )

    # Delete OTP after use
    await redis.delete(key)

    # Find user
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account not found or deactivated.")

    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    logger.info("auth.otp.verified", user_id=user.id, email=user.email)
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


# ── Refresh Token Rotation ─────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Refresh access token (with rotation)",
    description="Provide a valid refresh token. Returns new access + refresh pair. Old refresh token is invalidated.",
)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user_id = payload.get("sub")
    old_jti = payload.get("jti")
    old_exp = payload.get("exp", 0)

    # Check if old refresh token was already blacklisted (replay attack detection)
    if old_jti:
        from backend.services.token_blacklist import is_token_blacklisted
        if await is_token_blacklisted(old_jti):
            logger.warning("auth.refresh.replay_detected", user_id=user_id, jti=old_jti)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token already used. Please log in again.",
            )

    # Verify user still exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    # Blacklist the old refresh token (rotation)
    if old_jti:
        await blacklist_token(old_jti, old_exp)

    # Issue new token pair
    access_token = create_access_token(data={"sub": user.id})
    new_refresh_token = create_refresh_token(data={"sub": user.id})

    return RefreshResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


# ── Logout ─────────────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Logout (blacklist current token)",
)
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
):
    # Extract the token from the Authorization header
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = decode_token(token)
        if payload:
            jti = payload.get("jti")
            exp = payload.get("exp", 0)
            if jti:
                await blacklist_token(jti, exp)

    logger.info("auth.logout", user_id=user.id)
    return MessageResponse(message="Successfully logged out.")


# ── Account Deletion ───────────────────────────────────────────────────────────

@router.delete(
    "/account",
    response_model=MessageResponse,
    summary="Delete account (soft-delete)",
    description="Immediately deactivates the account. Hard deletion scheduled after 30 days.",
)
async def delete_account(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Soft-delete: deactivate user
    await db.execute(
        update(User).where(User.id == user.id).values(is_active=False)
    )

    # Blacklist current token
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = decode_token(token)
        if payload and payload.get("jti"):
            await blacklist_token(payload["jti"], payload.get("exp", 0))

    logger.info("auth.account_deleted", user_id=user.id, email=user.email)
    return MessageResponse(
        message="Account deactivated. It will be permanently deleted after 30 days. Contact support to cancel."
    )


# ── Get Current User ───────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
)
async def me(user: User = Depends(get_current_user)):
    return user
