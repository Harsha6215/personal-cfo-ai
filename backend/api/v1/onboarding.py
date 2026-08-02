"""
Onboarding API — Epic 6 Sprint 6.4

Endpoints:
    GET  /api/v1/onboarding/profile  — get current user's onboarding profile
    PUT  /api/v1/onboarding/profile  — update onboarding profile (any step)
    POST /api/v1/onboarding/complete — mark onboarding as complete
    GET  /api/v1/onboarding/status   — get onboarding completion status
"""

from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.user import User
from backend.models.user_profile import UserProfile

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Onboarding"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    risk_appetite: str | None = None
    investment_horizon: str | None = None
    monthly_income: float | None = None
    age: int | None = None
    primary_goals: list[str] | None = None
    experience_level: str | None = None
    onboarding_step: int | None = None


class ProfileResponse(BaseModel):
    id: str
    user_id: str
    risk_appetite: str | None = None
    investment_horizon: str | None = None
    monthly_income: float | None = None
    age: int | None = None
    primary_goals: list[str] | None = None
    experience_level: str | None = None
    onboarding_step: int = 0
    onboarding_completed_at: str | None = None

    model_config = {"from_attributes": True}


class OnboardingStatus(BaseModel):
    completed: bool
    current_step: int
    total_steps: int = 6


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get(
    "/profile",
    response_model=ProfileResponse,
    summary="Get onboarding profile",
)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        # Auto-create profile on first access
        profile = UserProfile(user_id=user.id, onboarding_step=0)
        db.add(profile)
        await db.flush()
        await db.refresh(profile)

    return profile


@router.put(
    "/profile",
    response_model=ProfileResponse,
    summary="Update onboarding profile",
    description="Update any fields. Use during each onboarding step.",
)
async def update_profile(
    body: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = UserProfile(user_id=user.id, onboarding_step=0)
        db.add(profile)
        await db.flush()
        await db.refresh(profile)

    # Update fields that were provided
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.flush()
    await db.refresh(profile)

    logger.info(
        "onboarding.profile_updated",
        user_id=user.id,
        step=profile.onboarding_step,
        fields=list(update_data.keys()),
    )
    return profile


@router.post(
    "/complete",
    response_model=ProfileResponse,
    summary="Mark onboarding as complete",
)
async def complete_onboarding(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found. Start onboarding first.")

    profile.onboarding_step = 6
    profile.onboarding_completed_at = datetime.now(timezone.utc).isoformat()

    await db.flush()
    await db.refresh(profile)

    logger.info("onboarding.completed", user_id=user.id)
    return profile


@router.get(
    "/status",
    response_model=OnboardingStatus,
    summary="Get onboarding completion status",
)
async def get_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        return OnboardingStatus(completed=False, current_step=0)

    return OnboardingStatus(
        completed=profile.onboarding_completed_at is not None,
        current_step=profile.onboarding_step,
    )
