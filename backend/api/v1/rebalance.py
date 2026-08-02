"""
Rebalancer API — Story 5.5

POST /api/v1/decisions/rebalance — generate rebalance plan
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
from backend.services.allocation_engine import AllocationEngine
from backend.services.market_data import MarketDataService, YahooFinanceProvider
from backend.services.portfolio_engine import PortfolioEngine
from backend.services.rebalancer import PortfolioRebalancer

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Rebalance"])


class RebalanceOrderResponse(BaseModel):
    ticker: str
    name: str
    action: str
    quantity: int
    estimated_price: float
    estimated_amount: float
    reason: str
    priority: int


class RebalancePlanResponse(BaseModel):
    orders: list[RebalanceOrderResponse]
    total_buy_amount: float
    total_sell_amount: float
    net_cash_needed: float
    estimated_charges: float
    tax_note: str
    summary: str


class RebalanceRequest(BaseModel):
    available_cash: float = 0
    strategy: str = "equal_weight"  # equal_weight or custom
    targets: dict[str, float] | None = None


@router.post(
    "/rebalance",
    response_model=RebalancePlanResponse,
    summary="Generate rebalance plan",
)
async def generate_rebalance_plan(
    body: RebalanceRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Portfolio).where(Portfolio.user_id == user.id).limit(1))
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="No portfolio found")

    engine = PortfolioEngine(db)
    holdings = await engine.calculate_holdings(portfolio.id)
    if not holdings:
        raise HTTPException(status_code=404, detail="No holdings to rebalance")

    total_value = sum(h.invested_value for h in holdings)
    holdings_data = [
        {"ticker": h.ticker, "name": h.name, "invested_value": h.invested_value, "asset_type": h.asset_type}
        for h in holdings
    ]

    # Compute allocation drift
    alloc_engine = AllocationEngine()
    if body.strategy == "custom" and body.targets:
        plan = alloc_engine.compute_custom(holdings_data, total_value, body.targets)
    else:
        plan = alloc_engine.compute_equal_weight(holdings_data, total_value)

    # Fetch current prices
    market = MarketDataService(provider=YahooFinanceProvider())
    prices = {}
    for h in holdings:
        try:
            quote = await market.get_quote(h.ticker)
            if quote:
                prices[h.ticker] = quote.price
        except Exception:
            prices[h.ticker] = h.average_cost  # fallback to avg cost

    # Generate rebalance orders
    rebalancer = PortfolioRebalancer()
    slots_data = [
        {"ticker": s.ticker, "name": s.name, "drift_pct": s.drift_pct,
         "action": s.action, "amount_to_adjust": s.amount_to_adjust}
        for s in plan.slots if s.action != "ON_TARGET"
    ]

    rebalance_plan = rebalancer.generate_plan(slots_data, prices, body.available_cash)

    return RebalancePlanResponse(
        orders=[RebalanceOrderResponse(**o.__dict__) for o in rebalance_plan.orders],
        total_buy_amount=rebalance_plan.total_buy_amount,
        total_sell_amount=rebalance_plan.total_sell_amount,
        net_cash_needed=rebalance_plan.net_cash_needed,
        estimated_charges=rebalance_plan.estimated_charges,
        tax_note=rebalance_plan.tax_note,
        summary=rebalance_plan.summary,
    )
