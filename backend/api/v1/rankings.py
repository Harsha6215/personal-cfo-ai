"""
Buy/Sell Rankings API — Story 5.6

GET /api/v1/decisions/rankings — get ranked buy/sell lists
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
from backend.services.decision_engine import DecisionEngine, PortfolioContext
from backend.services.market_data import MarketDataService, YahooFinanceProvider
from backend.services.portfolio_engine import PortfolioEngine
from backend.services.rankings_engine import RankingsEngine

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Rankings"])


class RankedStockResponse(BaseModel):
    rank: int
    ticker: str
    name: str
    action: str
    composite_score: float
    confidence: float
    momentum_score: float
    value_score: float
    risk_score: float
    suggested_action: str


class RankingsResponse(BaseModel):
    buy_list: list[RankedStockResponse]
    sell_list: list[RankedStockResponse]
    summary: str


@router.get(
    "/rankings",
    response_model=RankingsResponse,
    summary="Get buy/sell ranked lists",
)
async def get_rankings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate rankings from portfolio holdings using the Decision Engine."""
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id).limit(1))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="No portfolio found")

    engine = PortfolioEngine(db)
    holdings = await engine.calculate_holdings(portfolio.id)
    if not holdings:
        raise HTTPException(status_code=404, detail="No holdings found")

    # Build recommendations from agent mock scores (quick assessment)
    # In production, these come from cached Decision Engine results
    market = MarketDataService(provider=YahooFinanceProvider())
    decision = DecisionEngine()
    recommendations = []

    for h in holdings[:15]:  # limit to avoid rate limits
        try:
            quote = await market.get_quote(h.ticker)
            if not quote:
                continue

            # Quick heuristic scores based on market data
            price = quote.price or 0
            high = quote.high_52w or price
            low = quote.low_52w or price
            pe = quote.pe_ratio

            # Technical score: position in 52W range
            range_pct = (price - low) / (high - low) * 10 if high != low else 5
            tech_score = max(2, min(9, 10 - range_pct))  # lower price in range = more attractive

            # Value score from PE
            val_score = 7.0
            if pe and pe > 0:
                if pe < 15:
                    val_score = 8.5
                elif pe < 25:
                    val_score = 7.0
                elif pe < 40:
                    val_score = 5.5
                else:
                    val_score = 4.0

            # Risk score from volatility proxy
            volatility = (high - low) / price * 100 if price > 0 else 50
            risk_score = max(3, min(9, 10 - volatility / 10))

            agent_scores = {
                "financial_analyst": 6.5,  # neutral without real financials
                "valuation_specialist": val_score,
                "technical_analyst": tech_score,
                "news_analyst": 6.0,
                "risk_manager": risk_score,
                "macro_economist": 6.0,
            }

            rec = decision.recommend(h.ticker, agent_scores)
            company = await market.get_company_info(h.ticker)
            recommendations.append({
                "ticker": h.ticker,
                "name": company.name if company else h.name,
                "action": rec.action,
                "weighted_score": rec.weighted_score,
                "confidence": rec.confidence,
                "agent_scores": agent_scores,
            })
        except Exception:
            continue

    rankings_engine = RankingsEngine()
    rankings = rankings_engine.rank(recommendations)

    return RankingsResponse(
        buy_list=[RankedStockResponse(**s.__dict__) for s in rankings.buy_list],
        sell_list=[RankedStockResponse(**s.__dict__) for s in rankings.sell_list],
        summary=rankings.summary,
    )
