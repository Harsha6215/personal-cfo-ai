"""
Market Data API — live quotes, price history, company info.

All data flows through the MarketDataService abstraction.
"""

from datetime import date, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.core.auth import get_current_user
from backend.models.user import User
from backend.services.market_data import MarketDataService, YahooFinanceProvider

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Market Data"])

# Singleton service instance
_market_service = MarketDataService(provider=YahooFinanceProvider())


def get_market_service() -> MarketDataService:
    return _market_service


# ── Schemas ────────────────────────────────────────────────────────────────────

class QuoteResponse(BaseModel):
    ticker: str
    price: float
    change: float
    change_pct: float
    volume: int
    market_cap: float | None = None
    pe_ratio: float | None = None
    eps: float | None = None
    high_52w: float | None = None
    low_52w: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    prev_close: float | None = None
    currency: str = "INR"
    exchange: str = "NSE"


class PriceBarResponse(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    adj_close: float
    volume: int


class CompanyInfoResponse(BaseModel):
    ticker: str
    name: str
    sector: str | None = None
    industry: str | None = None
    description: str | None = None
    website: str | None = None
    employees: int | None = None
    country: str = "India"
    market_cap: float | None = None
    pe_ratio: float | None = None
    eps: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    high_52w: float | None = None
    low_52w: float | None = None


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get(
    "/quote/{ticker}",
    response_model=QuoteResponse,
    summary="Get live price quote",
    description="Returns current/latest price, change, volume, and key metrics for a ticker.",
)
async def get_quote(
    ticker: str,
    service: MarketDataService = Depends(get_market_service),
    user: User = Depends(get_current_user),
):
    quote = await service.get_quote(ticker.upper())
    if not quote:
        raise HTTPException(status_code=404, detail=f"No quote found for {ticker}")

    return QuoteResponse(
        ticker=quote.ticker,
        price=quote.price,
        change=quote.change,
        change_pct=quote.change_pct,
        volume=quote.volume,
        market_cap=quote.market_cap,
        pe_ratio=quote.pe_ratio,
        eps=quote.eps,
        high_52w=quote.high_52w,
        low_52w=quote.low_52w,
        day_high=quote.day_high,
        day_low=quote.day_low,
        prev_close=quote.prev_close,
        currency=quote.currency,
        exchange=quote.exchange,
    )


@router.get(
    "/history/{ticker}",
    response_model=list[PriceBarResponse],
    summary="Get price history (OHLCV)",
    description="Returns daily OHLCV bars for a ticker between two dates.",
)
async def get_history(
    ticker: str,
    days: int = Query(30, description="Number of days of history", le=365),
    service: MarketDataService = Depends(get_market_service),
    user: User = Depends(get_current_user),
):
    end = date.today()
    start = end - timedelta(days=days)

    bars = await service.get_history(ticker.upper(), start, end)
    if not bars:
        raise HTTPException(status_code=404, detail=f"No price history for {ticker}")

    return [
        PriceBarResponse(
            date=bar.date.isoformat(),
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            adj_close=bar.adj_close,
            volume=bar.volume,
        )
        for bar in bars
    ]


@router.get(
    "/company/{ticker}",
    response_model=CompanyInfoResponse,
    summary="Get company profile",
    description="Returns company fundamentals: sector, industry, market cap, PE, EPS, etc.",
)
async def get_company_info(
    ticker: str,
    service: MarketDataService = Depends(get_market_service),
    user: User = Depends(get_current_user),
):
    info = await service.get_company_info(ticker.upper())
    if not info:
        raise HTTPException(status_code=404, detail=f"No company info for {ticker}")

    return CompanyInfoResponse(
        ticker=info.ticker,
        name=info.name,
        sector=info.sector,
        industry=info.industry,
        description=info.description,
        website=info.website,
        employees=info.employees,
        country=info.country,
        market_cap=info.market_cap,
        pe_ratio=info.pe_ratio,
        eps=info.eps,
        dividend_yield=info.dividend_yield,
        beta=info.beta,
        high_52w=info.high_52w,
        low_52w=info.low_52w,
    )
