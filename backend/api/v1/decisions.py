"""
Decision Intelligence API — personalized, explainable recommendations.

POST /api/v1/decisions/recommend/:ticker — get personalized recommendation
"""

import time

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_current_user
from backend.core.database import get_db
from backend.models.portfolio import Portfolio
from backend.models.user import User
from backend.services.decision_engine import DecisionEngine, PortfolioContext
from backend.services.portfolio_engine import PortfolioEngine

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Decisions"])


class RecommendationResponse(BaseModel):
    ticker: str
    action: str
    confidence: float
    priority: str
    weighted_score: float
    reasoning: str
    evidence: list[str]
    agent_scores: dict[str, float]
    portfolio_context: str | None = None
    total_time_ms: int = 0


@router.post(
    "/recommend/{ticker}",
    response_model=RecommendationResponse,
    summary="Get personalized investment recommendation",
    description="Runs AI agents → Decision Engine → Portfolio Context → Final recommendation.",
)
async def get_recommendation(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    start = time.perf_counter()

    # 1. Run AI agents (from the existing AI endpoint logic)
    import sys, os
    _AI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ai-services"))
    if _AI_PATH not in sys.path:
        sys.path.insert(0, _AI_PATH)

    from agents.base import AgentContext
    from backend.api.v1.ai import _get_orchestrator
    from backend.services.market_data import MarketDataService, YahooFinanceProvider
    from backend.services.market_data.financials import fetch_financials
    from backend.services.market_data.news import fetch_news
    from datetime import date, timedelta

    market = MarketDataService(provider=YahooFinanceProvider())
    context = AgentContext(ticker=ticker.upper(), user_id=user.id)

    # Gather data
    quote = await market.get_quote(ticker.upper())
    if quote:
        context.quote = {"price": quote.price, "change": quote.change, "change_pct": quote.change_pct,
                         "volume": quote.volume, "pe_ratio": quote.pe_ratio, "eps": quote.eps,
                         "market_cap": quote.market_cap, "high_52w": quote.high_52w, "low_52w": quote.low_52w}

    company = await market.get_company_info(ticker.upper())
    if company:
        context.company_info = {"name": company.name, "sector": company.sector, "industry": company.industry,
                                "market_cap": company.market_cap, "pe_ratio": company.pe_ratio,
                                "eps": company.eps, "beta": company.beta}

    financials = await fetch_financials(ticker.upper(), "income", "quarterly")
    if financials:
        context.financials = {"income_quarterly": financials}

    news = await fetch_news(ticker.upper(), limit=5)
    if news:
        context.news = [{"title": a.title, "source": a.source, "published": a.published} for a in news]

    end_date = date.today()
    start_date = end_date - timedelta(days=200)
    bars = await market.get_history(ticker.upper(), start_date, end_date)
    if bars:
        context.price_history = [{"close": b.close} for b in bars]

    # 2. Run specialist agents
    orchestrator = _get_orchestrator()
    specialist_names = [n for n in orchestrator._agents if n not in ("chief_investment_officer", "portfolio_analyst")]
    responses = await orchestrator.run_selected(specialist_names, context)

    # 3. Extract scores
    agent_scores = {}
    for r in responses:
        if r.score is not None and r.score > 0:
            agent_scores[r.agent_name] = r.score
        else:
            agent_scores[r.agent_name] = 5.0  # neutral default

    # 4. Get portfolio context (Story 5.2)
    portfolio_ctx = None
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id).limit(1))
    portfolio = result.scalar_one_or_none()
    if portfolio:
        engine = PortfolioEngine(db)
        holdings = await engine.calculate_holdings(portfolio.id)
        if holdings:
            total = sum(h.invested_value for h in holdings)
            sector_alloc = {}
            has_stock = False
            existing_qty = 0
            for h in holdings:
                sector = h.asset_type  # simplified — use enriched sector later
                sector_alloc[sector] = sector_alloc.get(sector, 0) + (h.invested_value / total * 100 if total else 0)
                if h.ticker == ticker.upper():
                    has_stock = True
                    existing_qty = h.quantity

            top_pct = max((h.invested_value / total * 100 for h in holdings), default=0) if total else 0
            portfolio_ctx = PortfolioContext(
                total_holdings=len(holdings),
                total_invested=total,
                sector_allocation=sector_alloc,
                top_holding_pct=top_pct,
                has_stock=has_stock,
                existing_quantity=existing_qty,
            )

    # 5. Decision Engine
    decision = DecisionEngine()
    rec = decision.recommend(ticker.upper(), agent_scores, portfolio_ctx)

    total_time = int((time.perf_counter() - start) * 1000)

    return RecommendationResponse(
        ticker=rec.ticker,
        action=rec.action,
        confidence=rec.confidence,
        priority=rec.priority,
        weighted_score=rec.weighted_score,
        reasoning=rec.reasoning,
        evidence=rec.evidence,
        agent_scores=rec.agent_scores,
        portfolio_context=rec.portfolio_context,
        total_time_ms=total_time,
    )
