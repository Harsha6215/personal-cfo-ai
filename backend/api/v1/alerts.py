"""
Alerts Engine API — Story 5.8

GET /api/v1/decisions/alerts — get all active alerts
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
from backend.services.alerts_engine import AlertsEngine
from backend.services.market_data import MarketDataService, YahooFinanceProvider
from backend.services.market_data.factory import get_market_service as create_market_service
from backend.services.portfolio_engine import PortfolioEngine

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Alerts"])


class AlertResponse(BaseModel):
    id: str
    category: str
    severity: str
    title: str
    message: str
    ticker: str | None = None
    action_required: bool = False
    suggested_action: str | None = None


class AlertsSummaryResponse(BaseModel):
    alerts: list[AlertResponse]
    critical_count: int
    warning_count: int
    info_count: int
    total: int


@router.get(
    "/alerts",
    response_model=AlertsSummaryResponse,
    summary="Get portfolio alerts",
)
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id).limit(1))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        return AlertsSummaryResponse(alerts=[], critical_count=0, warning_count=0, info_count=0, total=0)

    engine = PortfolioEngine(db)
    holdings = await engine.calculate_holdings(portfolio.id)
    if not holdings:
        return AlertsSummaryResponse(alerts=[], critical_count=0, warning_count=0, info_count=0, total=0)

    total_value = sum(h.invested_value for h in holdings)
    holdings_data = [
        {"ticker": h.ticker, "name": h.name, "invested_value": h.invested_value, "asset_type": h.asset_type}
        for h in holdings
    ]

    # Fetch quotes for holdings
    market = create_market_service()
    quotes = {}
    for h in holdings[:20]:
        try:
            quote = await market.get_quote(h.ticker)
            if quote:
                quotes[h.ticker] = {
                    "price": quote.price,
                    "change_pct": quote.change_pct,
                    "high_52w": quote.high_52w,
                    "low_52w": quote.low_52w,
                }
        except Exception:
            continue

    alerts_engine = AlertsEngine()
    summary = alerts_engine.generate_all(holdings_data, total_value, quotes)

    return AlertsSummaryResponse(
        alerts=[
            AlertResponse(
                id=a.id, category=a.category, severity=a.severity,
                title=a.title, message=a.message, ticker=a.ticker,
                action_required=a.action_required, suggested_action=a.suggested_action,
            )
            for a in summary.alerts
        ],
        critical_count=summary.critical_count,
        warning_count=summary.warning_count,
        info_count=summary.info_count,
        total=summary.total,
    )
