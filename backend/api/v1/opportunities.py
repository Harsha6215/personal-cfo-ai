"""
Opportunity Scanner API — Story 5.4

GET /api/v1/decisions/opportunities — scan portfolio/watchlist for opportunities
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.portfolio import Portfolio
from backend.models.watchlist import WatchlistItem
from backend.models.user import User
from backend.services.market_data import MarketDataService, YahooFinanceProvider
from backend.services.opportunity_scanner import OpportunityScanner
from backend.services.portfolio_engine import PortfolioEngine

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Opportunities"])


class OpportunityResponse(BaseModel):
    ticker: str
    name: str
    opportunity_type: str
    score: float
    reason: str
    entry_price: float | None = None
    target_price: float | None = None
    upside_pct: float | None = None
    risk_level: str = "MEDIUM"
    evidence: list[str] = []


class ScanResultResponse(BaseModel):
    total_scanned: int
    opportunities: list[OpportunityResponse]
    summary: str


@router.get(
    "/opportunities",
    response_model=ScanResultResponse,
    summary="Scan for investment opportunities",
)
async def scan_opportunities(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    market = MarketDataService(provider=YahooFinanceProvider())
    scanner = OpportunityScanner()

    # Get symbols to scan (watchlist + holdings)
    symbols: set[str] = set()

    # From watchlist
    wl_result = await db.execute(select(WatchlistItem).where(WatchlistItem.user_id == user.id))
    watchlist_items = wl_result.scalars().all()
    symbols.update(item.symbol for item in watchlist_items)

    # From holdings
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id).limit(1))
    portfolio = result.scalar_one_or_none()
    if portfolio:
        engine = PortfolioEngine(db)
        holdings = await engine.calculate_holdings(portfolio.id)
        symbols.update(h.ticker for h in holdings)

    if not symbols:
        return ScanResultResponse(total_scanned=0, opportunities=[], summary="No stocks to scan. Add watchlist items or holdings first.")

    # Fetch quotes for all symbols
    quotes = []
    for sym in list(symbols)[:20]:  # limit to 20 to avoid rate limits
        try:
            quote = await market.get_quote(sym)
            if quote:
                company = await market.get_company_info(sym)
                quotes.append({
                    "ticker": sym,
                    "name": company.name if company else sym,
                    "price": quote.price,
                    "change_pct": quote.change_pct,
                    "high_52w": quote.high_52w,
                    "low_52w": quote.low_52w,
                    "pe_ratio": quote.pe_ratio,
                    "volume": quote.volume,
                })
        except Exception:
            continue

    # Run scanners
    value_opps = scanner.scan_value_dips(quotes)
    momentum_opps = scanner.scan_momentum(quotes)

    all_opps = value_opps + momentum_opps
    all_opps.sort(key=lambda o: o.score, reverse=True)

    return ScanResultResponse(
        total_scanned=len(quotes),
        opportunities=[
            OpportunityResponse(
                ticker=o.ticker, name=o.name, opportunity_type=o.opportunity_type,
                score=o.score, reason=o.reason, entry_price=o.entry_price,
                target_price=o.target_price, upside_pct=o.upside_pct,
                risk_level=o.risk_level, evidence=o.evidence,
            )
            for o in all_opps[:10]
        ],
        summary=f"Scanned {len(quotes)} stocks. Found {len(all_opps)} opportunities.",
    )
