"""
Daily CIO Report API — Story 5.12

GET /api/v1/decisions/cio-report — generate daily intelligence report
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
from backend.services.allocation_engine import AllocationEngine
from backend.services.cio_report import CIOReportGenerator
from backend.services.market_data import MarketDataService, YahooFinanceProvider
from backend.services.portfolio_engine import PortfolioEngine

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["CIO Report"])


class MarketSnapshotResponse(BaseModel):
    nifty50: float | None = None
    nifty50_change_pct: float | None = None
    sensex: float | None = None
    sensex_change_pct: float | None = None
    market_mood: str = "neutral"


class PortfolioSnapshotResponse(BaseModel):
    total_invested: float = 0
    total_holdings: int = 0
    top_gainers: list[dict] = []
    top_losers: list[dict] = []
    needs_rebalance: bool = False


class CIOReportResponse(BaseModel):
    report_date: str
    greeting: str
    market: MarketSnapshotResponse
    portfolio: PortfolioSnapshotResponse
    top_recommendations: list[dict] = []
    alerts_summary: dict = {}
    opportunities: list[dict] = []
    risks_to_watch: list[str] = []
    action_items: list[str] = []


@router.get(
    "/cio-report",
    response_model=CIOReportResponse,
    summary="Generate Daily CIO Report",
)
async def get_cio_report(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    market_svc = MarketDataService(provider=YahooFinanceProvider())

    # ── Market data ────────────────────────────────────────────────────────────
    market_data = {}
    try:
        nifty = await market_svc.get_quote("^NSEI")
        if nifty:
            market_data["nifty50"] = nifty.price
            market_data["nifty50_change_pct"] = nifty.change_pct
        sensex = await market_svc.get_quote("^BSESN")
        if sensex:
            market_data["sensex"] = sensex.price
            market_data["sensex_change_pct"] = sensex.change_pct
    except Exception:
        pass

    # ── Portfolio data ─────────────────────────────────────────────────────────
    portfolio_data = {}
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id).limit(1))
    portfolio = result.scalar_one_or_none()

    holdings_data = []
    total_value = 0
    quotes = {}

    if portfolio:
        engine = PortfolioEngine(db)
        holdings = await engine.calculate_holdings(portfolio.id)
        total_value = sum(h.invested_value for h in holdings)
        holdings_data = [
            {"ticker": h.ticker, "name": h.name, "invested_value": h.invested_value, "asset_type": h.asset_type}
            for h in holdings
        ]

        # Fetch quotes for top holdings
        top_gainers = []
        top_losers = []
        for h in holdings[:15]:
            try:
                quote = await market_svc.get_quote(h.ticker)
                if quote:
                    quotes[h.ticker] = {
                        "price": quote.price, "change_pct": quote.change_pct,
                        "high_52w": quote.high_52w, "low_52w": quote.low_52w,
                    }
                    if quote.change_pct > 0:
                        top_gainers.append({"ticker": h.ticker, "change_pct": quote.change_pct})
                    else:
                        top_losers.append({"ticker": h.ticker, "change_pct": quote.change_pct})
            except Exception:
                continue

        top_gainers.sort(key=lambda x: x["change_pct"], reverse=True)
        top_losers.sort(key=lambda x: x["change_pct"])

        # Check if rebalance needed
        alloc_engine = AllocationEngine()
        plan = alloc_engine.compute_equal_weight(holdings_data, total_value)

        portfolio_data = {
            "total_invested": total_value,
            "total_holdings": len(holdings),
            "top_gainers": top_gainers[:3],
            "top_losers": top_losers[:3],
            "needs_rebalance": plan.needs_rebalance,
            "concentration_warnings": [
                s.ticker for s in plan.slots if s.actual_pct > 25
            ],
        }

    # ── Alerts ─────────────────────────────────────────────────────────────────
    alerts_engine = AlertsEngine()
    alerts_result = alerts_engine.generate_all(holdings_data, total_value, quotes)
    alerts_summary = {
        "critical": alerts_result.critical_count,
        "warning": alerts_result.warning_count,
        "info": alerts_result.info_count,
        "total": alerts_result.total,
    }

    # ── Generate report ────────────────────────────────────────────────────────
    generator = CIOReportGenerator()
    report = generator.generate(
        market_data=market_data,
        portfolio_data=portfolio_data,
        alerts=alerts_summary,
    )

    return CIOReportResponse(
        report_date=report.report_date,
        greeting=report.greeting,
        market=MarketSnapshotResponse(
            nifty50=report.market.nifty50,
            nifty50_change_pct=report.market.nifty50_change_pct,
            sensex=report.market.sensex,
            sensex_change_pct=report.market.sensex_change_pct,
            market_mood=report.market.market_mood,
        ),
        portfolio=PortfolioSnapshotResponse(
            total_invested=report.portfolio.total_invested,
            total_holdings=report.portfolio.total_holdings,
            top_gainers=report.portfolio.top_gainers,
            top_losers=report.portfolio.top_losers,
            needs_rebalance=report.portfolio.needs_rebalance,
        ),
        top_recommendations=report.top_recommendations,
        alerts_summary=alerts_summary,
        opportunities=report.opportunities,
        risks_to_watch=report.risks_to_watch,
        action_items=report.action_items,
    )
