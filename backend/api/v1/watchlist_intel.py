"""
Watchlist Intelligence API — Story 5.7

GET /api/v1/decisions/watchlist — get watchlist with intelligence signals
"""

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.user import User
from backend.models.watchlist import WatchlistItem
from backend.services.market_data import MarketDataService, YahooFinanceProvider
from backend.services.watchlist_intelligence import WatchlistIntelligence

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Watchlist Intelligence"])


class WatchlistInsightResponse(BaseModel):
    ticker: str
    name: str
    current_price: float
    change_pct: float
    target_price: float | None = None
    stop_loss: float | None = None
    distance_to_target_pct: float | None = None
    signal: str = "NEUTRAL"
    signal_reason: str = ""
    sentiment: str = "neutral"
    risk_level: str = "MEDIUM"
    composite_score: float | None = None
    alerts: list[str] = []


class WatchlistReportResponse(BaseModel):
    items: list[WatchlistInsightResponse]
    actionable_count: int
    total_items: int
    summary: str


@router.get(
    "/watchlist",
    response_model=WatchlistReportResponse,
    summary="Get watchlist with intelligence signals",
)
async def get_watchlist_intelligence(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Get watchlist items
    result = await db.execute(select(WatchlistItem).where(WatchlistItem.user_id == user.id))
    items = result.scalars().all()

    if not items:
        return WatchlistReportResponse(items=[], actionable_count=0, total_items=0, summary="No watchlist items.")

    # Fetch quotes
    market = MarketDataService(provider=YahooFinanceProvider())
    watchlist_data = []
    quotes = {}

    for item in items:
        try:
            quote = await market.get_quote(item.symbol)
            if quote:
                quotes[item.symbol] = {
                    "price": quote.price,
                    "change_pct": quote.change_pct,
                    "high_52w": quote.high_52w,
                    "low_52w": quote.low_52w,
                }
                company = await market.get_company_info(item.symbol)
                watchlist_data.append({
                    "ticker": item.symbol,
                    "name": company.name if company else item.symbol,
                    "notes": item.notes,
                    "target_price": None,  # could be parsed from notes
                    "stop_loss": None,
                })
        except Exception:
            continue

    # Run intelligence analysis
    intel = WatchlistIntelligence()
    report = intel.analyze(watchlist_data, quotes)

    return WatchlistReportResponse(
        items=[
            WatchlistInsightResponse(
                ticker=i.ticker, name=i.name, current_price=i.current_price,
                change_pct=i.change_pct, target_price=i.target_price,
                stop_loss=i.stop_loss, distance_to_target_pct=i.distance_to_target_pct,
                signal=i.signal, signal_reason=i.signal_reason,
                sentiment=i.sentiment, risk_level=i.risk_level,
                composite_score=i.composite_score, alerts=i.alerts,
            )
            for i in report.items
        ],
        actionable_count=report.actionable_count,
        total_items=report.total_items,
        summary=report.summary,
    )
