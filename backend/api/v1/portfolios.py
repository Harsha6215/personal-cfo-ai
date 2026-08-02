"""
Portfolio API — CRUD and event queries.

Portfolios are the top-level container. Holdings are computed from events.
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.portfolio import Portfolio
from backend.models.asset import Asset, AssetType, Exchange
from backend.models.financial_event import FinancialEvent, EventType
from backend.models.user import User
from backend.services.portfolio_engine import PortfolioEngine

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Portfolio"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class PortfolioResponse(BaseModel):
    id: str
    name: str
    currency: str
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PortfolioCreate(BaseModel):
    name: str
    currency: str = "INR"
    description: str | None = None


class AddHoldingRequest(BaseModel):
    """Manually add a BUY event to a portfolio."""
    ticker: str
    name: str
    quantity: float
    price: float
    asset_type: str = "STOCK"
    exchange: str = "NSE"
    notes: str | None = None


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


# ── Holdings (computed from events) ───────────────────────────────────────────

class HoldingComputed(BaseModel):
    asset_id: str
    ticker: str
    name: str
    asset_type: str
    quantity: float
    average_cost: float
    invested_value: float


class HoldingsResponse(BaseModel):
    portfolio_id: str
    portfolio_name: str
    total_invested: float
    total_holdings: int
    total_events: int
    holdings: list[HoldingComputed]


@router.get(
    "/{portfolio_id}/holdings",
    response_model=HoldingsResponse,
    summary="Get computed holdings (derived from events)",
    description="Replays all financial events and returns current positions with cost basis.",
)
async def get_portfolio_holdings(
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

    # Calculate
    engine = PortfolioEngine(db)
    summary = await engine.get_summary(portfolio_id)

    return HoldingsResponse(
        portfolio_id=portfolio.id,
        portfolio_name=portfolio.name,
        total_invested=summary.total_invested,
        total_holdings=summary.total_holdings,
        total_events=summary.total_events,
        holdings=[
            HoldingComputed(
                asset_id=h.asset_id,
                ticker=h.ticker,
                name=h.name,
                asset_type=h.asset_type,
                quantity=h.quantity,
                average_cost=h.average_cost,
                invested_value=h.invested_value,
            )
            for h in summary.holdings
        ],
    )


# ── Manual Add Holding ─────────────────────────────────────────────────────────

@router.post(
    "/{portfolio_id}/add-holding",
    status_code=status.HTTP_201_CREATED,
    summary="Manually add a holding (BUY event)",
    description="Creates an asset (if needed) and a BUY financial event. No CSV upload required.",
)
async def add_holding(
    portfolio_id: str,
    body: AddHoldingRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify portfolio ownership
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Find or create asset
    ticker = body.ticker.upper().strip()
    result = await db.execute(select(Asset).where(Asset.ticker == ticker).limit(1))
    asset = result.scalar_one_or_none()

    if asset is None:
        asset = Asset(
            ticker=ticker,
            name=body.name,
            asset_type=AssetType(body.asset_type) if body.asset_type in [e.value for e in AssetType] else AssetType.STOCK,
            exchange=Exchange(body.exchange) if body.exchange in [e.value for e in Exchange] else Exchange.NSE,
            currency=portfolio.currency,
        )
        db.add(asset)
        await db.flush()
        await db.refresh(asset)

    # Create BUY event
    event = FinancialEvent(
        portfolio_id=portfolio_id,
        asset_id=asset.id,
        event_type=EventType.BUY,
        quantity=body.quantity,
        price=body.price,
        amount=body.quantity * body.price,
        fees=0,
        executed_at=datetime.now(timezone.utc),
        source="manual",
        exchange=body.exchange,
        notes=body.notes,
    )
    db.add(event)
    await db.flush()

    logger.info(
        "portfolio.holding_added",
        portfolio_id=portfolio_id,
        ticker=ticker,
        quantity=body.quantity,
        price=body.price,
        user_id=user.id,
    )

    return {
        "status": "added",
        "ticker": ticker,
        "quantity": body.quantity,
        "price": body.price,
        "invested": body.quantity * body.price,
        "asset_id": asset.id,
        "event_id": event.id,
    }


# ── Edit Holding ───────────────────────────────────────────────────────────────

class EditHoldingRequest(BaseModel):
    """Edit quantity and/or price of a holding's BUY events."""
    quantity: float | None = None
    price: float | None = None
    name: str | None = None


@router.put(
    "/{portfolio_id}/holdings/{ticker}",
    summary="Edit a holding (update quantity/price)",
    description="Updates the most recent BUY event for this ticker. Use for corrections.",
)
async def edit_holding(
    portfolio_id: str,
    ticker: str,
    body: EditHoldingRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify portfolio ownership
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Find the asset
    result = await db.execute(select(Asset).where(Asset.ticker == ticker.upper()).limit(1))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {ticker} not found")

    # Get the most recent BUY event for this asset in this portfolio
    result = await db.execute(
        select(FinancialEvent)
        .where(
            FinancialEvent.portfolio_id == portfolio_id,
            FinancialEvent.asset_id == asset.id,
            FinancialEvent.event_type.in_([EventType.BUY, EventType.SIP]),
        )
        .order_by(FinancialEvent.executed_at.desc())
        .limit(1)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail=f"No BUY event found for {ticker}")

    # Update fields
    if body.quantity is not None:
        event.quantity = body.quantity
        event.amount = body.quantity * float(event.price)
    if body.price is not None:
        event.price = body.price
        event.amount = float(event.quantity) * body.price
    if body.name is not None:
        asset.name = body.name

    await db.flush()
    logger.info("portfolio.holding_edited", portfolio_id=portfolio_id, ticker=ticker, user_id=user.id)

    return {
        "status": "updated",
        "ticker": ticker.upper(),
        "quantity": float(event.quantity),
        "price": float(event.price),
        "invested": float(event.amount),
    }


# ── Delete Holding ─────────────────────────────────────────────────────────────

@router.delete(
    "/{portfolio_id}/holdings/{ticker}",
    summary="Delete a holding (remove all events for this ticker)",
    description="Removes all financial events for this ticker from the portfolio.",
)
async def delete_holding(
    portfolio_id: str,
    ticker: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify portfolio ownership
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Find the asset
    result = await db.execute(select(Asset).where(Asset.ticker == ticker.upper()).limit(1))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {ticker} not found")

    # Delete all events for this asset in this portfolio
    from sqlalchemy import delete
    result = await db.execute(
        delete(FinancialEvent).where(
            FinancialEvent.portfolio_id == portfolio_id,
            FinancialEvent.asset_id == asset.id,
        )
    )
    deleted_count = result.rowcount

    logger.info(
        "portfolio.holding_deleted",
        portfolio_id=portfolio_id,
        ticker=ticker,
        events_deleted=deleted_count,
        user_id=user.id,
    )

    return {
        "status": "deleted",
        "ticker": ticker.upper(),
        "events_removed": deleted_count,
    }
