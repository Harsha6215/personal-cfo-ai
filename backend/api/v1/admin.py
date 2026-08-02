"""
Admin API — Sprint 6.5

All endpoints require admin role (via require_admin dependency).
Provides user management, metrics overview, AI usage stats, and audit log access.
"""

from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import require_admin
from backend.core.database import get_db
from backend.models.audit_log import AuditLog
from backend.models.base import new_uuid
from backend.models.user import User, UserRole
from backend.services.metrics import (
    get_active_users_today,
    get_error_count_today,
    get_latency_percentiles,
    get_llm_total_today,
    get_request_count_today,
)

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Admin"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class UserListItem(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime


class UserDetail(UserListItem):
    updated_at: datetime


class MetricsResponse(BaseModel):
    requests_today: int
    errors_today: int
    latency_p50: float
    latency_p95: float
    active_users_today: int


class AIUsageResponse(BaseModel):
    llm_calls_today: int


class AuditLogEntry(BaseModel):
    id: str
    admin_user_id: str
    action: str
    target_type: str
    target_id: str
    details: Optional[dict] = None
    created_at: datetime


class MessageResponse(BaseModel):
    message: str


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _create_audit_log(
    db: AsyncSession,
    admin_user_id: str,
    action: str,
    target_type: str,
    target_id: str,
    details: dict | None = None,
) -> None:
    """Create an audit log entry."""
    entry = AuditLog(
        id=new_uuid(),
        admin_user_id=admin_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
    )
    db.add(entry)
    await db.commit()


# ── User Management ───────────────────────────────────────────────────────────


@router.get("/users", response_model=list[UserListItem])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with basic info."""
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return [
        UserListItem(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role.value,
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.get("/users/{user_id}", response_model=UserDetail)
async def get_user_detail(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed user information."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserDetail(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/users/{user_id}/deactivate", response_model=MessageResponse)
async def deactivate_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user.is_active = False
    await db.commit()

    await _create_audit_log(
        db, admin.id, "user.deactivate", "user", user_id,
        details={"email": user.email},
    )
    logger.info("admin.user_deactivated", user_id=user_id, admin_id=admin.id)
    return MessageResponse(message=f"User {user.email} deactivated")


@router.post("/users/{user_id}/activate", response_model=MessageResponse)
async def activate_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Activate a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = True
    await db.commit()

    await _create_audit_log(
        db, admin.id, "user.activate", "user", user_id,
        details={"email": user.email},
    )
    logger.info("admin.user_activated", user_id=user_id, admin_id=admin.id)
    return MessageResponse(message=f"User {user.email} activated")


# ── Metrics ────────────────────────────────────────────────────────────────────


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(admin: User = Depends(require_admin)):
    """Get aggregate platform metrics."""
    latency = await get_latency_percentiles()
    return MetricsResponse(
        requests_today=await get_request_count_today(),
        errors_today=await get_error_count_today(),
        latency_p50=latency["p50"],
        latency_p95=latency["p95"],
        active_users_today=await get_active_users_today(),
    )


# ── AI Usage ───────────────────────────────────────────────────────────────────


@router.get("/ai-usage", response_model=AIUsageResponse)
async def get_ai_usage(admin: User = Depends(require_admin)):
    """Get LLM usage statistics."""
    return AIUsageResponse(
        llm_calls_today=await get_llm_total_today(),
    )


# ── Audit Log ──────────────────────────────────────────────────────────────────


@router.get("/audit", response_model=list[AuditLogEntry])
async def get_audit_log(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get audit log entries, newest first."""
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    )
    entries = result.scalars().all()
    return [
        AuditLogEntry(
            id=e.id,
            admin_user_id=e.admin_user_id,
            action=e.action,
            target_type=e.target_type,
            target_id=e.target_id,
            details=e.details,
            created_at=e.created_at,
        )
        for e in entries
    ]
