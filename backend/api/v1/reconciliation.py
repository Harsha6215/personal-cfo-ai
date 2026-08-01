"""
Reconciliation API — detect discrepancies between imports.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.portfolio import Portfolio
from backend.models.user import User
from backend.services.reconciliation import ReconciliationService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Reconciliation"])


class AlertResponse(BaseModel):
    ticker: str
    asset_id: str
    alert_type: str
    previous_qty: float
    current_qty: float
    difference: float
    message: str


@router.get(
    "/alerts",
    response_model=list[AlertResponse],
    summary="Get reconciliation alerts",
    description="Compares latest import against previous state. Flags quantity changes, new/closed positions.",
)
async def get_reconciliation_alerts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Get user's first portfolio
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id).limit(1)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return []

    service = ReconciliationService(db)
    alerts = await service.reconcile(portfolio.id)

    return [
        AlertResponse(
            ticker=a.ticker,
            asset_id=a.asset_id,
            alert_type=a.alert_type,
            previous_qty=a.previous_qty,
            current_qty=a.current_qty,
            difference=a.difference,
            message=a.message,
        )
        for a in alerts
    ]
