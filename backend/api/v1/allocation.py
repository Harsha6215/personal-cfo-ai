"""
Allocation Engine API — Story 5.3

GET  /api/v1/decisions/allocation — get allocation plan for portfolio
POST /api/v1/decisions/allocation — compute with custom targets
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
from backend.services.allocation_engine import AllocationEngine
from backend.services.portfolio_engine import PortfolioEngine

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Allocation"])


class AllocationSlotResponse(BaseModel):
    ticker: str
    name: str
    target_pct: float
    actual_pct: float
    drift_pct: float
    action: str
    amount_to_adjust: float


class AllocationPlanResponse(BaseModel):
    strategy: str
    total_value: float
    slots: list[AllocationSlotResponse]
    max_drift: float
    needs_rebalance: bool
    summary: str
    sector_allocation: dict[str, float] = {}


class CustomTargetsRequest(BaseModel):
    targets: dict[str, float]  # {ticker: target_pct}


@router.get(
    "/allocation",
    response_model=AllocationPlanResponse,
    summary="Get equal-weight allocation plan",
)
async def get_allocation(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id).limit(1))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="No portfolio found")

    engine = PortfolioEngine(db)
    holdings = await engine.calculate_holdings(portfolio.id)
    if not holdings:
        raise HTTPException(status_code=404, detail="No holdings found")

    total_value = sum(h.invested_value for h in holdings)
    holdings_data = [
        {"ticker": h.ticker, "name": h.name, "invested_value": h.invested_value, "asset_type": h.asset_type}
        for h in holdings
    ]

    alloc = AllocationEngine()
    plan = alloc.compute_equal_weight(holdings_data, total_value)
    sector_alloc = alloc.compute_sector_allocation(holdings_data, total_value)

    return AllocationPlanResponse(
        strategy=plan.strategy,
        total_value=plan.total_value,
        slots=[AllocationSlotResponse(**s.__dict__) for s in plan.slots],
        max_drift=plan.max_drift,
        needs_rebalance=plan.needs_rebalance,
        summary=plan.summary,
        sector_allocation=sector_alloc,
    )


@router.post(
    "/allocation",
    response_model=AllocationPlanResponse,
    summary="Compute allocation with custom targets",
)
async def compute_custom_allocation(
    body: CustomTargetsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id).limit(1))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="No portfolio found")

    engine = PortfolioEngine(db)
    holdings = await engine.calculate_holdings(portfolio.id)
    if not holdings:
        raise HTTPException(status_code=404, detail="No holdings found")

    total_value = sum(h.invested_value for h in holdings)
    holdings_data = [
        {"ticker": h.ticker, "name": h.name, "invested_value": h.invested_value, "asset_type": h.asset_type}
        for h in holdings
    ]

    alloc = AllocationEngine()
    plan = alloc.compute_custom(holdings_data, total_value, body.targets)

    return AllocationPlanResponse(
        strategy=plan.strategy,
        total_value=plan.total_value,
        slots=[AllocationSlotResponse(**s.__dict__) for s in plan.slots],
        max_drift=plan.max_drift,
        needs_rebalance=plan.needs_rebalance,
        summary=plan.summary,
    )
