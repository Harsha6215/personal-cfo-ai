"""
Price API — historical OHLCV data + portfolio performance chart.
"""

from datetime import date, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.portfolio import Portfolio
from backend.models.user import User
from backend.services.market_data import MarketDataService, YahooFinanceProvider
from backend.services.market_data.factory import get_market_service as create_market_service
from backend.services.portfolio_engine import PortfolioEngine

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Prices"])

_market_service = create_market_service()


class PricePoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class PortfolioPerformancePoint(BaseModel):
    date: str
    value: float


@router.get(
    "/history/{ticker}",
    response_model=list[PricePoint],
    summary="Get price history for a ticker",
)
async def get_price_history(
    ticker: str,
    days: int = Query(365, le=3650, description="Days of history"),
    user: User = Depends(get_current_user),
):
    end = date.today()
    start = end - timedelta(days=days)
    bars = await _market_service.get_history(ticker.upper(), start, end)
    if not bars:
        raise HTTPException(status_code=404, detail=f"No price history for {ticker}")
    return [
        PricePoint(
            date=bar.date.isoformat(),
            open=bar.open, high=bar.high, low=bar.low, close=bar.close,
            volume=bar.volume,
        )
        for bar in bars
    ]


@router.get(
    "/portfolio-performance",
    response_model=list[PortfolioPerformancePoint],
    summary="Portfolio value over time",
    description="Calculates daily portfolio value using historical prices for each holding.",
)
async def get_portfolio_performance(
    days: int = Query(365, le=3650),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Get user's portfolio and current holdings
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user.id).limit(1)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return []

    engine = PortfolioEngine(db)
    holdings = await engine.calculate_holdings(portfolio.id)
    if not holdings:
        return []

    # Fetch historical prices for all holdings
    end = date.today()
    start = end - timedelta(days=days)

    # Get price history for each holding
    ticker_histories: dict[str, dict[str, float]] = {}  # ticker -> {date_str: close_price}
    for h in holdings:
        bars = await _market_service.get_history(h.ticker, start, end)
        if bars:
            ticker_histories[h.ticker] = {
                bar.date.isoformat(): bar.close for bar in bars
            }

    if not ticker_histories:
        return []

    # Get all unique dates (sorted)
    all_dates = sorted(set(
        d for prices in ticker_histories.values() for d in prices.keys()
    ))

    # Calculate portfolio value for each date
    performance: list[PortfolioPerformancePoint] = []
    for d in all_dates:
        total_value = 0.0
        for h in holdings:
            price = ticker_histories.get(h.ticker, {}).get(d)
            if price:
                total_value += h.quantity * price
            else:
                # Use average cost as fallback if no price for this date
                total_value += h.invested_value

        performance.append(PortfolioPerformancePoint(
            date=d,
            value=round(total_value, 2),
        ))

    return performance
