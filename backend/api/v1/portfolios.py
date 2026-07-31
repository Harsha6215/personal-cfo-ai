"""
Portfolio API — CRUD and event queries.

Portfolios are the top-level container. Holdings are computed from events.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.portfolio import Portfolio
from backend.models.financial_event import FinancialEvent, EventType
from backend.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Portfolio"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class PortfolioResponse(BaseModel):
    id: str
    name: str
    currency: str
    description: str | None
    created_at: str

    model_config = {"from_attributes": True}


class PortfolioCreate(BaseModel):
    name: str
    currency: str = "INR"
    description: str | None = None


class PortfolioSummary(BaseModel):
    portfolio_id: str
    name: str
    total_events: int
    total_assets: int
    total_invested: float


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[PortfolioResponse],
    summary="List user's portfolios",
)
async def list_portfolios(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id).order_by(Portfolio.created_at)
    )
    return result.scalars().all()


@router.post(
    "",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a portfolio",
)
async def create_portfolio(
    body: PortfolioCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolio = Portfolio(
        user_id=user.id,
        name=body.name,
        currency=body.currency,
        description=body.description,
    )
    db.add(portfolio)
    await db.flush()
    await db.refresh(portfolio)
    logger.info("portfolio.created", portfolio_id=portfolio.id, user_id=user.id)
    return portfolio


@router.get(
    "/{portfolio_id}",
    response_model=PortfolioResponse,
    summary="Get portfolio by ID",
)
async def get_portfolio(
    portfolio_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.get(
    "/{portfolio_id}/summary",
    response_model=PortfolioSummary,
    summary="Get portfolio summary (event counts)",
)
async def get_portfolio_summary(
    portfolio_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify ownership
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Count events
    event_count = await db.execute(
        select(func.count(FinancialEvent.id)).where(FinancialEvent.portfolio_id == portfolio_id)
    )
    total_events = event_count.scalar() or 0

    # Count unique assets
    asset_count = await db.execute(
        select(func.count(func.distinct(FinancialEvent.asset_id))).where(
            FinancialEvent.portfolio_id == portfolio_id
        )
    )
    total_assets = asset_count.scalar() or 0

    # Sum invested (BUY + SIP amounts)
    invested = await db.execute(
        select(func.coalesce(func.sum(FinancialEvent.amount), 0)).where(
            FinancialEvent.portfolio_id == portfolio_id,
            FinancialEvent.event_type.in_([EventType.BUY, EventType.SIP]),
        )
    )
    total_invested = float(invested.scalar() or 0)

    return PortfolioSummary(
        portfolio_id=portfolio.id,
        name=portfolio.name,
        total_events=total_events,
        total_assets=total_assets,
        total_invested=total_invested,
    )
